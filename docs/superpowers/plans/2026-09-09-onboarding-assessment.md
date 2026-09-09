# Onboarding Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Assessment backend minimum loop for versioned onboarding questionnaires, resumable answers, deterministic scoring, result snapshots, and pending profile fact candidates.

**Architecture:** Add an `assessment` module beside `profile`, `conversation`, and `safety`. Keep questionnaire templates and answers in their own relational tables; the service owns user scoping, answer validation, deterministic scoring, coverage thresholds, and candidate fact creation. Do not call an LLM or write directly to `health_facts` in this phase.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 async ORM, Alembic, MySQL 8.0, pytest, HTTPX.

**Spec:** `docs/superpowers/specs/2026-09-09-onboarding-assessment-design.md`

## Global Constraints

- All routes derive `user_id` from the authenticated user and never accept it from the client.
- Raw answers, candidate facts, and confirmed health facts remain separate data classes.
- The baseline score is a deterministic rule result, not a medical or disease score.
- Low coverage returns coverage and a short result but no total score.
- Safety answers create independent safety handling and never affect ordinary score arithmetic.
- No real passwords, API keys, complete medication text, or unnecessary health text in tests, logs, or audit records.
- Every database change must support `upgrade head`, downgrade to the previous revision, and upgrade again.

### Task 1: Define schemas and deterministic scoring

**Files:**
- Create: `backend/app/assessment/__init__.py`
- Create: `backend/app/assessment/schemas.py`
- Create: `backend/app/assessment/scoring.py`
- Test: `backend/tests/test_assessment_scoring.py`

- [x] Write failing tests for coverage thresholds, weighted dimension scores, skipped answers, and no-score low coverage.
- [x] Run the scoring tests and verify they fail because the Assessment module does not exist.
- [x] Implement Pydantic schemas and a pure scoring function with explicit version and evidence output.
- [x] Run the scoring tests and verify they pass.

### Task 2: Add SQLAlchemy models and migration

**Files:**
- Create: `backend/app/models/assessment.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0003_create_assessment.py`
- Modify: `backend/tests/test_models.py`
- Modify: `backend/tests/test_migration_config.py`

- [x] Add failing metadata tests for templates, questions, submissions, answers, and fact candidates without raw-text leakage.
- [x] Run the model tests and verify they fail because the tables are not registered.
- [x] Implement the five models with user-scoped foreign keys, version fields, JSON answer/rule data, status fields, and no delete cascade.
- [x] Add the incremental migration and reversible downgrade.
- [x] Run model tests, `alembic upgrade head`, `alembic downgrade 0002_safety_events`, `alembic upgrade head`, and `alembic check`.

### Task 3: Implement repository and service behavior

**Files:**
- Create: `backend/app/assessment/repository.py`
- Create: `backend/app/assessment/service.py`
- Test: `backend/tests/test_assessment_service.py`

- [x] Write failing service tests for onboarding state, user-scoped draft creation, answer validation, resumable unanswered questions, completion snapshots, and pending candidates.
- [x] Run the service tests and verify they fail because the repository and service do not exist.
- [x] Implement the minimum repository and service methods using the existing async repository patterns.
- [x] Ensure completion is idempotent for the same submission state and rejects cross-user access.
- [x] Run the service tests and verify they pass.

### Task 4: Expose authenticated API routes

**Files:**
- Create: `backend/app/assessment/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_assessment_api.py`

- [x] Write failing HTTP tests for onboarding state, draft creation, answer update, completion, result retrieval, and cross-user rejection.
- [x] Run the API tests and verify they fail because routes are not registered.
- [x] Implement routes using `get_current_user`, stable validation/resource errors, and the Assessment service dependency.
- [x] Run the API tests and verify they pass.

### Task 5: Sync documentation and verify the feature

**Files:**
- Modify: `当前项目进度.md`
- Modify: `软件架构设计文档.md`
- Modify: `产品需求文档.md`

- [ ] Update progress with the actual implemented subset and remaining professional question-bank review.
- [ ] Update architecture with exact status transitions and implemented API boundary.
- [ ] Update acceptance references from AC-01..AC-17 to AC-01..AC-21 where applicable.
- [ ] Run the full backend test suite, Ruff, Alembic check, and `git diff --check`.
- [ ] Inspect status and preserve unrelated existing changes and ignored caches.
