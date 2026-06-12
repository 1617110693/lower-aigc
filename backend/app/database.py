"""
数据库引擎与会话管理 (Database Engine & Session Configuration)

使用 SQLAlchemy 2.0 异步引擎，配合 aiosqlite 驱动实现全异步数据库访问。
所有 ORM 模型继承自统一的 Base 类，表结构在应用启动时自动创建。

架构说明：
  - engine: 全局异步数据库引擎，由应用启动时初始化一次
  - async_session: 会话工厂，每个请求通过 get_db() 获取独立的数据库会话
  - Base: 所有 ORM 模型的基类，维护元数据注册表

扩展指南：
  如需切换到 PostgreSQL/MySQL，只需修改 .env 中的 DATABASE_URL，
  并将 aiosqlite 替换为对应的异步驱动（asyncpg / asyncmy）。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 创建异步数据库引擎
# echo=True 在开发环境会打印所有 SQL 语句，方便调试
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
)

# 异步会话工厂
# expire_on_commit=False: 提交后不使对象过期，避免后续访问触发懒加载异常
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """
    声明式 ORM 基类

    所有数据库表模型都需继承此基类。
    Base.metadata 中自动收集所有继承类的表定义，
    init_db() 通过 Base.metadata.create_all() 一次性创建全部表。
    """


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入: 提供数据库会话

    在每个 HTTP 请求处理期间创建独立的数据库会话，
    请求正常完成时自动提交 (commit)，
    发生异常时自动回滚 (rollback)，确保数据一致性。

    用法（在 FastAPI 端点中）:
        @router.get("/something")
        async def something(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库表结构

    在应用启动 (lifespan) 时调用。
    如果表不存在则创建；如果已存在则跳过（不会覆盖数据）。
    注意: 修改模型后需要手动执行 Alembic 迁移，此方法只负责建表。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
