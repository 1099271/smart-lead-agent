import logging
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import FastAPI, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from config import settings
from database.connection import get_db, engine, Base
from database import repository, models
from core.search import SearchModule
from core.analysis import AnalysisModule
from core.generation import GenerationModule
from core.schemas import ContactInfo, GeneratedEmail
from core.email.smtp_sender import SMTPEmailSender
from core.email.esp_sender import ESPEmailSender
from core.email.base_sender import BaseEmailSender

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建数据库表（如果不存在）
Base.metadata.create_all(bind=engine)

# 全局变量，用于存储初始化的模块
search_module: SearchModule = None
analysis_module: AnalysisModule = None
generation_module: GenerationModule = None
email_sender: BaseEmailSender = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 的生命周期管理函数。
    在应用启动时初始化所有模块，在关闭时清理资源。
    """
    global search_module, analysis_module, generation_module, email_sender

    logger.info("Initializing Smart Lead Agent modules...")

    # 初始化 HTTP 客户端（用于搜索）
    http_client = httpx.Client(timeout=30.0)
    search_module = SearchModule(http_client)

    # 初始化 OpenAI 客户端（用于分析和生成）
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    analysis_module = AnalysisModule(openai_client)
    generation_module = GenerationModule(openai_client)

    # 初始化邮件发送器（优先使用ESP，如果未配置则使用SMTP）
    try:
        if settings.SENDGRID_API_KEY:
            email_sender = ESPEmailSender()
            logger.info("Using ESP (SendGrid) for email sending")
        elif settings.SMTP_HOST:
            email_sender = SMTPEmailSender()
            logger.info("Using SMTP for email sending")
        else:
            raise ValueError(
                "No email configuration found. Please configure either SENDGRID_API_KEY or SMTP settings."
            )
    except Exception as e:
        logger.error(f"Failed to initialize email sender: {e}")
        raise

    logger.info("All modules initialized successfully")

    yield  # 应用运行中

    # 清理资源
    logger.info("Shutting down Smart Lead Agent...")
    http_client.close()
    logger.info("Shutdown complete")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="Smart Lead Agent API",
    description="自动化潜在客户开发系统",
    version="1.0.0",
    lifespan=lifespan,
)


# API 请求/响应模型
class LeadGenerationRequest(BaseModel):
    company_name: str
    search_queries: List[str] = [
        "{company_name} 采购经理",
        "{company_name} 采购负责人",
        "{company_name} procurement manager",
        "{company_name} 供应链经理",
    ]


class LeadGenerationResponse(BaseModel):
    success: bool
    company_id: int
    contact_id: int | None = None
    email_id: int | None = None
    message: str
    error: str | None = None


@app.get("/")
async def root():
    """API 根端点，返回系统信息。"""
    return {
        "service": "Smart Lead Agent API",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "healthy"}


@app.post("/generate-lead", response_model=LeadGenerationResponse)
async def generate_lead(
    request: LeadGenerationRequest, db=Depends(get_db)
) -> LeadGenerationResponse:
    """
    主要的潜在客户生成端点。
    接收一个公司名称，执行完整的流程：搜索、分析、生成邮件、发送邮件。

    流程步骤：
    1. 获取或创建公司记录
    2. 执行搜索查询
    3. 分析搜索结果，提取联系人信息
    4. 如果找到联系人，生成个性化邮件
    5. 发送邮件并记录结果
    """
    repo = repository.Repository(db)

    try:
        # 步骤 1: 获取或创建公司记录
        logger.info(f"Processing company: {request.company_name}")
        company = repo.get_or_create_company(request.company_name)

        # 更新公司状态为处理中
        company.status = models.CompanyStatus.processing
        db.commit()

        # 步骤 2: 执行搜索
        logger.info(f"Executing search queries for {request.company_name}")
        search_results = search_module.search_for_company(
            request.company_name, request.search_queries
        )

        if not search_results:
            company.status = models.CompanyStatus.failed
            db.commit()
            return LeadGenerationResponse(
                success=False,
                company_id=company.id,
                message="No search results found",
                error="Search did not return any results",
            )

        # 步骤 3: 分析搜索结果，提取联系人信息
        logger.info("Analyzing search results to extract contact information")
        contact_info = analysis_module.find_contact(
            search_results, request.company_name
        )

        if not contact_info:
            company.status = models.CompanyStatus.failed
            db.commit()
            return LeadGenerationResponse(
                success=False,
                company_id=company.id,
                message="No contact information found in search results",
                error="Analysis module could not extract valid contact information",
            )

        # 检查联系人是否已存在
        existing_contact = repo.get_contact_by_email(contact_info.email)
        if existing_contact:
            logger.info(f"Contact with email {contact_info.email} already exists")
            contact = existing_contact
        else:
            # 步骤 4: 创建联系人记录
            logger.info(f"Creating contact record for {contact_info.email}")
            contact = repo.create_contact(contact_info, company.id)

        # 步骤 5: 生成个性化邮件
        logger.info("Generating personalized email")
        generated_email = generation_module.generate_cold_email(
            contact_info, request.company_name
        )

        # 步骤 6: 创建邮件记录
        email_record = repo.create_email(generated_email, contact.id)

        # 步骤 7: 发送邮件
        logger.info(f"Sending email to {contact_info.email}")
        send_status = email_sender.send(contact_info.email, generated_email)

        if send_status.success:
            # 更新邮件状态为已发送
            repo.update_email_status(
                email_record.id,
                models.EmailStatus.sent,
                error_message=None,
            )
            # 更新公司状态为已联系
            company.status = models.CompanyStatus.contacted
            db.commit()

            logger.info(
                f"Successfully completed lead generation for {request.company_name}"
            )
            return LeadGenerationResponse(
                success=True,
                company_id=company.id,
                contact_id=contact.id,
                email_id=email_record.id,
                message="Lead generation completed successfully. Email sent.",
            )
        else:
            # 更新邮件状态为失败
            repo.update_email_status(
                email_record.id,
                models.EmailStatus.failed,
                error_message=send_status.error,
            )
            company.status = models.CompanyStatus.failed
            db.commit()

            return LeadGenerationResponse(
                success=False,
                company_id=company.id,
                contact_id=contact.id,
                email_id=email_record.id,
                message="Email generation succeeded but sending failed",
                error=send_status.error,
            )

    except Exception as e:
        logger.error(f"An error occurred during lead generation: {e}", exc_info=True)
        # 尝试更新公司状态为失败
        try:
            company = (
                db.query(models.Company)
                .filter(models.Company.name == request.company_name)
                .first()
            )
            if company:
                company.status = models.CompanyStatus.failed
                db.commit()
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
