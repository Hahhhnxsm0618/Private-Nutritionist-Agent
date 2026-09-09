from pathlib import Path

from app.models import Base


def test_initial_migration_file_exists() -> None:
    """基础迁移是新环境初始化数据库的入口。"""
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0001_create_database_foundation.py"

    assert migration.exists()


def test_initial_migration_contains_all_foundation_tables() -> None:
    """初始迁移覆盖第一批基础表，后续表由增量迁移负责。"""
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0001_create_database_foundation.py"
    ).read_text(encoding="utf-8")

    foundation_tables = set(Base.metadata.tables) - {
        "safety_events",
        "assessment_templates",
        "assessment_questions",
        "assessment_submissions",
        "assessment_answers",
        "assessment_fact_candidates",
    }
    for table_name in foundation_tables:
        assert f"'{table_name}'" in migration


def test_safety_events_incremental_migration_exists() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0002_create_safety_events.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0002_safety_events"' in migration
    assert 'down_revision: str | Sequence[str] | None = "0001_foundation"' in migration
    assert 'op.create_table(\n        "safety_events"' in migration
    assert 'op.drop_table("safety_events")' in migration


def test_assessment_incremental_migration_exists() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0003_create_assessment.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0003_assessment"' in migration
    assert 'down_revision: str | Sequence[str] | None = "0002_safety_events"' in migration
    for table_name in (
        "assessment_templates",
        "assessment_questions",
        "assessment_submissions",
        "assessment_answers",
        "assessment_fact_candidates",
    ):
        assert f'"{table_name}"' in migration
