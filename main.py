import logging
from fastapi import FastAPI
from database.connection import engine, Base
from findkp.router import router as findkp_router

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建数据库表（如果不存在）
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用实例
app = FastAPI(
    title="Smart Lead Agent API",
    description="自动化潜在客户开发系统 - 三大板块: FindKP, MailManager, Writer",
    version="2.0.0",
)


# 注册路由
app.include_router(findkp_router)


@app.get("/")
async def root():
    """API 根端点,返回系统信息"""
    return {
        "service": "Smart Lead Agent API",
        "version": "2.0.0",
        "status": "operational",
        "modules": ["FindKP", "MailManager (待实现)", "Writer (待实现)"],
    }


@app.get("/health")
async def health_check():
    """全局健康检查端点"""
    return {"status": "healthy", "message": "Smart Lead Agent is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
