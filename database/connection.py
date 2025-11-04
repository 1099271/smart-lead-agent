from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import settings

# 构建异步数据库连接URL（使用 aiomysql）
DATABASE_URL = (
    f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# 创建异步数据库引擎
# pool_pre_ping=True: 在每次从连接池中获取连接时，发送一个简单的 "ping" 查询，
# 以检查连接是否仍然有效。这有助于处理数据库服务器重启或网络问题导致的连接断开。
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 创建一个Base类，我们定义的ORM模型将继承这个类
Base = declarative_base()


async def get_db():
    """
    FastAPI 依赖项，用于获取异步数据库会话。

    这个异步生成器函数会在每个请求开始时创建一个新的数据库会话，
    在请求处理完成后（无论成功或失败）关闭它。
    这种模式确保了每个请求都在其自己的数据库事务中运行，并且资源得到妥善管理。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
