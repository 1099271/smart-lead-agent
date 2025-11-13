"""OAuth 2.0 回调管理器

用于管理 Gmail OAuth 2.0 授权流程中的回调处理
使用数据库进行跨进程通信（CLI 和 FastAPI 是不同的进程）

设计思路：
1. FastAPI 收到回调后，保存到数据库
2. CLI 执行时，先检查数据库中是否有回调记录
3. 如果有，直接使用；如果没有，启动授权流程并提示用户完成授权后重试
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from logs import logger
from database.repository import Repository


class OAuth2CallbackManager:
    """OAuth 2.0 回调管理器

    使用数据库进行跨进程通信
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """初始化回调管理器

        Args:
            db: 数据库会话（可选，如果提供则可以直接使用）
        """
        self._db = db

    async def set_authorization_code(
        self, code: str, state: Optional[str] = None, db: Optional[AsyncSession] = None
    ):
        """设置授权码并保存到数据库（供 CLI 进程读取）

        Args:
            code: 从 Google 返回的授权码
            state: 状态参数（必需，用于标识授权流程）
            db: 数据库会话（如果未在 __init__ 中提供）

        Raises:
            ValueError: 如果 state 为空
        """
        if not state:
            raise ValueError("state 参数不能为空，用于标识授权流程")

        session = db or self._db
        if not session:
            raise ValueError("需要提供数据库会话")

        repository = Repository(session)
        try:
            await repository.create_oauth2_callback(
                state=state,
                code=code,
                expires_in_seconds=300,  # 5 分钟过期
            )
            logger.info(f"收到 OAuth 2.0 授权码，已保存到数据库 (state: {state})")
        except Exception as e:
            logger.error(f"保存 OAuth 2.0 回调到数据库失败: {e}", exc_info=True)
            raise

    async def set_error(
        self, error: str, state: Optional[str] = None, db: Optional[AsyncSession] = None
    ):
        """设置错误信息并保存到数据库

        Args:
            error: 错误信息
            state: 状态参数（必需，用于标识授权流程）
            db: 数据库会话（如果未在 __init__ 中提供）

        Raises:
            ValueError: 如果 state 为空
        """
        if not state:
            raise ValueError("state 参数不能为空，用于标识授权流程")

        session = db or self._db
        if not session:
            raise ValueError("需要提供数据库会话")

        repository = Repository(session)
        try:
            await repository.create_oauth2_callback(
                state=state,
                error=error,
                expires_in_seconds=300,  # 5 分钟过期
            )
            logger.error(
                f"OAuth 2.0 授权失败: {error}，已保存到数据库 (state: {state})"
            )
        except Exception as e:
            logger.error(f"保存 OAuth 2.0 错误到数据库失败: {e}", exc_info=True)
            raise

    async def get_callback(
        self, state: str, db: Optional[AsyncSession] = None, consume: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """从数据库获取 OAuth 2.0 回调记录

        Args:
            state: OAuth 2.0 state 参数（用于标识授权流程）
            db: 数据库会话（如果未在 __init__ 中提供）
            consume: 是否标记为已消费（默认 True）

        Returns:
            tuple: (authorization_code, error) 如果成功返回 (code, None)，失败返回 (None, error)，不存在返回 (None, None)

        Raises:
            ValueError: 如果 state 为空或没有提供数据库会话
        """
        if not state:
            raise ValueError("state 参数不能为空")

        session = db or self._db
        if not session:
            raise ValueError("需要提供数据库会话")

        repository = Repository(session)
        try:
            callback = await repository.get_oauth2_callback_by_state(
                state=state, consume=consume
            )

            if not callback:
                # 没有找到回调记录
                return None, None

            # 找到回调记录
            if callback.error:
                error_msg = callback.error
                logger.error(f"从数据库读取到错误: {error_msg} (state: {state})")
                return None, error_msg

            if callback.code:
                code = callback.code
                logger.info(f"从数据库读取到授权码 (state: {state})")
                return code, None

            # 既没有 code 也没有 error，返回 None
            return None, None

        except Exception as e:
            logger.error(f"查询 OAuth 2.0 回调失败: {e}", exc_info=True)
            raise

    def reset(self):
        """重置管理器状态（数据库版本无需重置）"""
        # 数据库版本不需要重置，因为使用 state 作为唯一标识
        pass


def get_oauth2_manager(db: Optional[AsyncSession] = None) -> OAuth2CallbackManager:
    """获取 OAuth 2.0 回调管理器实例

    Args:
        db: 数据库会话（可选）

    Returns:
        OAuth2CallbackManager: 回调管理器实例
    """
    return OAuth2CallbackManager(db=db)
