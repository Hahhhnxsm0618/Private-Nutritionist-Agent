from app.models import Base

EXPECTED_TABLES = {
    # 这里锁定数据库基础层的表集合，防止模型被意外遗漏或重复注册。
    "users",
    "auth_sessions",
    "health_profiles",
    "health_facts",
    "consents",
    "conversations",
    "messages",
    "idempotency_keys",
    "audit_logs",
    "safety_events",
    "assessment_templates",
    "assessment_questions",
    "assessment_submissions",
    "assessment_answers",
    "assessment_fact_candidates",
    "assessment_reviews",
}


def test_foundation_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_user_owned_tables_have_user_id_and_primary_keys_are_strings() -> None:
    """除用户主表外，业务数据都必须能按 user_id 做隔离。"""
    global_tables = {"assessment_templates", "assessment_questions", "assessment_reviews"}
    for table_name in EXPECTED_TABLES - {"users"} - global_tables:
        table = Base.metadata.tables[table_name]
        assert "user_id" in table.columns
        assert table.primary_key.columns[0].type.length == 36


def test_users_email_is_unique() -> None:
    """登录标识必须由数据库保证唯一，而不只依赖业务代码检查。"""
    users = Base.metadata.tables["users"]
    email = users.columns["email"]

    assert email.unique is True


def test_metadata_has_no_delete_cascade_foreign_keys() -> None:
    """删除策略由业务流程控制，避免级联误删健康和审计数据。"""
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.ondelete != "CASCADE"


def test_safety_events_store_structured_rule_results_without_raw_content() -> None:
    safety_events = Base.metadata.tables["safety_events"]

    assert {
        "user_id",
        "conversation_id",
        "message_id",
        "risk_level",
        "trigger_category",
        "rule_version",
        "action",
        "result",
        "request_id",
        "trace_id",
        "created_at",
    } <= set(safety_events.columns.keys())
    assert "content" not in safety_events.columns
    assert "raw_text" not in safety_events.columns


def test_assessment_tables_keep_answers_and_candidates_separate() -> None:
    templates = Base.metadata.tables["assessment_templates"]
    questions = Base.metadata.tables["assessment_questions"]
    submissions = Base.metadata.tables["assessment_submissions"]
    answers = Base.metadata.tables["assessment_answers"]
    candidates = Base.metadata.tables["assessment_fact_candidates"]

    assert {"code", "version", "status", "rule_version"} <= set(templates.columns.keys())
    assert {"template_id", "code", "tier", "options_json", "scoring_rule_json"} <= set(
        questions.columns.keys()
    )
    assert {"user_id", "template_id", "status", "coverage", "result_json"} <= set(
        submissions.columns.keys()
    )
    assert {"user_id", "submission_id", "question_id", "answer_json", "answer_status"} <= set(
        answers.columns.keys()
    )
    assert {"user_id", "submission_id", "fact_type", "value_json", "status", "health_fact_id"} <= set(
        candidates.columns.keys()
    )
    assert "content" not in answers.columns
    assert "content" not in candidates.columns


def test_assessment_reviews_record_professional_decision_without_raw_content() -> None:
    reviews = Base.metadata.tables["assessment_reviews"]

    assert {
        "published_by_user_id",
    } <= set(Base.metadata.tables["assessment_templates"].columns.keys())

    assert {
        "template_id",
        "reviewer_user_id",
        "status",
        "rule_version",
        "reviewed_at",
        "created_at",
    } <= set(reviews.columns.keys())
    assert "raw_text" not in reviews.columns
