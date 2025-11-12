import logging
from fastapi import FastAPI
from findkp.router import router as findkp_router
from writer.router import router as writer_router

# 导入 logs 模块以初始化日志配置（包括 httpx 日志级别设置）
import logs  # noqa: F401

# 设置日志（为了向后兼容，保留基本的 logging 配置）
# 但实际应用中推荐使用 loguru（通过 logs 模块）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI(
    title="Smart Lead Agent API",
    description="自动化潜在客户开发系统 - 三大板块: FindKP, MailManager, Writer",
    version="2.0.0",
)


# 注册路由
app.include_router(findkp_router)
app.include_router(writer_router)


@app.get("/")
async def root():
    """API 根端点,返回系统信息"""
    return {
        "service": "Smart Lead Agent API",
        "version": "2.0.0",
        "status": "operational",
        "modules": ["FindKP", "MailManager (待实现)", "Writer"],
    }


@app.get("/health")
async def health_check():
    """全局健康检查端点"""
    return {"status": "healthy", "message": "Smart Lead Agent is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
