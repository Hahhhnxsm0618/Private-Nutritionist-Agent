# Database Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first MySQL 8.0 migration and SQLAlchemy 2 model layer for authentication, user isolation, health facts, conversations, idempotency, and audit records.

**Architecture:** Use an async SQLAlchemy engine with a shared declarative base and focused model modules. Alembic imports the same metadata and creates nine tables in dependency order; application deletion remains explicit, so foreign keys do not cascade-delete user data.

**Tech Stack:** Python 3.11+, SQLAlchemy 2, Alembic, aiomysql, pydantic-settings, MySQL 8.0, pytest, Ruff, uv.

**Spec:** `docs/superpowers/specs/2026-09-09-database-foundation-design.md`

## Global Constraints

- Use the project MySQL instance at `127.0.0.1:3307` and database `nutrition_agent`.
- Reuse the external Milvus instance at `127.0.0.1:19530`; no Milvus tables or containers are added.
- Use UUID strings as primary keys and UTC `DATETIME(6)` timestamps.
- Store statuses as strings and validate them in Python/domain code rather than MySQL native ENUM values.
- Every user-owned resource carries `user_id` and repository queries will later require user scope.
- Do not store plaintext passwords or session tokens.

---

### Task 1: Database dependency and test contract

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Create: `backend/tests/test_models.py`
- Create: `backend/tests/test_database_config.py`

**Interfaces:**
- Produces importable `app.db.base.Base`, `app.db.session.engine`, `app.models` metadata, and a database URL setting.

- [x] Add SQLAlchemy, Alembic, aiomysql, and pydantic-settings dependencies.
- [x] Write tests asserting the nine table names, primary-key shape, user ownership columns, and configured MySQL URL.
- [x] Run the focused tests and verify they fail because the database modules and models do not exist.

### Task 2: SQLAlchemy base, settings, and models

**Files:**
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/profile.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/audit.py`
- Create: `backend/app/models/__init__.py`

**Interfaces:**
- `app.models.Base.metadata` exposes `users`, `auth_sessions`, `health_profiles`, `health_facts`, `consents`, `conversations`, `messages`, `idempotency_keys`, and `audit_logs`.
- `app.db.session.settings.database_url` reads `DATABASE_URL` and defaults to the project MySQL URL.
- `app.db.session.async_session_factory` creates `AsyncSession` instances.

- [x] Implement the shared declarative base, naming convention, UUID string type, and UTC timestamp mixin.
- [x] Implement the nine models with explicit foreign keys, unique constraints, indexes, JSON fields, and no delete cascades.
- [x] Run the focused tests and verify the model contract passes.
- [x] Run Ruff and the complete backend test suite.

### Task 3: Alembic migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_create_database_foundation.py`
- Modify: `backend/README.md`

**Interfaces:**
- `alembic upgrade head` creates the nine foundation tables.
- `alembic downgrade base` removes only those nine tables.

- [x] Configure Alembic to read `DATABASE_URL` and import `app.models.Base.metadata`.
- [x] Write the initial migration in dependency order with explicit indexes and constraints.
- [x] Run `alembic upgrade head` against the real local MySQL database.
- [x] Inspect `SHOW TABLES` and `alembic current`.
- [x] Run `alembic downgrade base`, confirm tables are removed, then run `alembic upgrade head` again.
- [x] Document migration commands in `backend/README.md`.

### Task 4: Progress and final verification

**Files:**
- Modify: `当前项目进度.md`
- Modify: `docs/superpowers/specs/2026-09-09-database-foundation-design.md`

- [x] Record the migration, model, and real-MySQL verification results.
- [x] Mark only completed foundation items; keep authentication and business workflows open.
- [x] Run pytest, Ruff, frontend build, Compose validation, and final database status checks.
