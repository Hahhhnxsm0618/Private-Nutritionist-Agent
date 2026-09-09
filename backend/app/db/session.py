"""数据库连接和会话配置。

这里有三个容易混淆的对象：

* ``engine`` 是应用与数据库之间的连接管理器，内部维护连接池；
* ``async_session_factory`` 是创建数据库会话的工厂；
* ``get_db_session`` 每次请求创建一个短生命周期的 ``AsyncSession``。

数据库地址从环境变量读取，默认值只用于本地开发；业务代码通过依赖函数获取
短生命周期的异步会话，避免多个请求直接共享同一个 Session 实例。
"""

from collections.abc import AsyncIterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Settings(BaseSettings):
    """应用所需的外部服务配置。

    Pydantic Settings 会按照字段名读取环境变量。例如 ``DATABASE_URL`` 会被
    读取到 ``database_url`` 字段。类型声明还会帮助 Pydantic 校验配置格式。
    """

    # 连接字符串的格式是：数据库驱动://用户名:密码@主机:端口/数据库名。
    # ``mysql+aiomysql`` 中的 aiomysql 表示使用支持 async/await 的 MySQL 驱动。
    # 默认端口与项目本地 Docker 配置保持一致；部署时应通过环境变量覆盖密码。
    database_url: str = "mysql+aiomysql://nutrition:nutrition-local@127.0.0.1:3307/nutrition_agent"
    # Milvus 是后续知识库向量检索使用的服务。现在先集中配置，避免未来在多个
    # 业务文件里重复写死地址。
    milvus_uri: str = "http://127.0.0.1:19530"
    jwt_secret_key: str = "local-development-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # ``env_file`` 允许从项目目录的 .env 文件加载本地配置。
    # ``extra="ignore"`` 表示 .env 中存在本类没有声明的变量时忽略它们，避免
    # 因为数据库配置之外的环境变量导致 Settings 初始化失败。
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# 模块加载时创建一次配置对象。后续 import settings 的地方都读取同一份配置，
# 不会每次请求都重新解析 .env 文件。
settings = Settings()
# Engine 不等于一条数据库连接，而是连接池和 SQL 执行入口。
# pool_pre_ping 会在使用连接前先做可用性检查，降低数据库连接闲置失效造成的报错。
engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
# Session 工厂负责创建 AsyncSession。
# expire_on_commit=False 表示 commit 后仍可读取对象属性，不需要立即再次查询数据库。
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """为一个请求提供异步数据库会话，并在退出时自动释放资源。

    ``yield`` 让 FastAPI 可以把这个函数当作依赖注入函数：路由执行前取得
    session，路由执行结束后离开 ``async with``，自动关闭 session。这样即使
    请求抛出异常，也不会把数据库连接长期占用。
    """
    async with async_session_factory() as session:
        yield session
