from pathlib import Path

from app.models import Base


def test_initial_migration_file_exists() -> None:
    """基础迁移是新环境初始化数据库的入口。"""
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_create_database_foundation.py"

    assert migration.exists()


def test_initial_migration_contains_all_foundation_tables() -> None:
    """迁移必须覆盖 ORM 元数据声明的全部基础表。"""
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0001_create_database_foundation.py"
    ).read_text(encoding="utf-8")

    for table_name in Base.metadata.tables:
        assert f"'{table_name}'" in migration
