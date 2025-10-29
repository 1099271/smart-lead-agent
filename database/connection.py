from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import settings

# 构建数据库连接URL
DATABASE_URL = (
    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# 创建数据库引擎
# pool_pre_ping=True: 在每次从连接池中获取连接时，发送一个简单的 "ping" 查询，
# 以检查连接是否仍然有效。这有助于处理数据库服务器重启或网络问题导致的连接断开。
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 创建一个SessionLocal类，用于创建数据库会话
# autocommit=False 和 autoflush=False 是 FastAPI/SQLAlchemy 集成的标准做法，
# 确保在事务块中可以精确控制何时将更改刷新和提交到数据库。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建一个Base类，我们定义的ORM模型将继承这个类
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖项，用于获取数据库会话。

    这个生成器函数会在每个请求开始时创建一个新的数据库会话，
    在请求处理完成后（无论成功或失败）关闭它。
    这种模式确保了每个请求都在其自己的数据库事务中运行，并且资源得到妥善管理。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
