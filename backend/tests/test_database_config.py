from app.db.session import settings


def test_database_url_defaults_to_project_mysql() -> None:
    """默认配置应指向项目约定的本地 MySQL 服务。"""
    assert settings.database_url.startswith("mysql+aiomysql://")
    assert "@127.0.0.1:3307/" in settings.database_url
