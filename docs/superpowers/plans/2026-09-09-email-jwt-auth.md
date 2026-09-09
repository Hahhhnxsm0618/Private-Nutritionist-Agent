# V0 Email JWT Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build V0 email/password registration, JWT access authentication, rotating refresh sessions, and logout for the FastAPI backend.

**Architecture:** Keep JWT access tokens stateless and short-lived, while storing only hashed opaque refresh tokens in the existing `auth_sessions` table. Isolate password/token primitives in an auth security module, application behavior in an auth service, and HTTP concerns in an auth router with a reusable `current_user` dependency.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, MySQL 8.0, PyJWT, pwdlib Argon2id, pytest, HTTPX.

**Spec:** `docs/superpowers/specs/2026-09-09-email-jwt-auth-design.md`

## Global Constraints

- Access Token lifetime is 30 minutes.
- Refresh Token lifetime is 30 days and is stored only as a SHA-256 hash.
- Passwords are stored only as Argon2id hashes.
- Unknown email and wrong password use the same authentication failure response.
- Third-party login remains V2 and is outside this plan.
- Every new behavior must have a failing test observed before implementation.
- Every completed stage must update `当前项目进度.md`.

### Task 1: Add Auth Dependencies and Settings

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `.env.example`
- Modify: `backend/app/db/session.py`
- Test: `backend/tests/test_auth_config.py`

**Interfaces:**
- Produces `settings.jwt_secret_key`, `settings.jwt_algorithm`, `settings.access_token_expire_minutes`, and `settings.refresh_token_expire_days`.

- [ ] Write a test asserting the four settings exist and use 30 minutes/30 days defaults.
- [ ] Run `pytest backend/tests/test_auth_config.py -q` and observe failure because settings do not exist.
- [ ] Add `PyJWT` and `pwdlib[argon2]` dependencies and the four settings, with the secret required from environment in non-test deployment configuration.
- [ ] Run the focused test and then `ruff check backend`.
- [ ] Update `.env.example` with a development JWT secret placeholder and durations.

### Task 2: Implement Password and Token Primitives

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/security.py`
- Test: `backend/tests/test_auth_security.py`

**Interfaces:**
- `hash_password(password: str) -> str`
- `verify_password(password: str, password_hash: str) -> bool`
- `create_access_token(user_id: str, settings: Settings) -> str`
- `decode_access_token(token: str, settings: Settings) -> str`
- `generate_refresh_token() -> str`
- `hash_refresh_token(token: str) -> str`

- [ ] Write tests for Argon2 verification, wrong-password rejection, JWT subject/type/expiry, invalid token rejection, and refresh-token hash non-reversibility.
- [ ] Run the focused tests and observe failure because the module is absent.
- [ ] Implement the smallest security module using `pwdlib.PasswordHash.recommended()`, `secrets.token_urlsafe`, `hashlib.sha256`, and PyJWT.
- [ ] Run focused security tests and refactor only after green.

### Task 3: Add Auth Schemas and Service Contracts

**Files:**
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/service.py`
- Test: `backend/tests/test_auth_service.py`

**Interfaces:**
- `RegisterRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`, `UserResponse` Pydantic models.
- `AuthService.register`, `.login`, `.refresh`, `.logout`, and `.get_current_user` async methods.

- [ ] Write service tests covering normalized email registration, duplicate registration, login failure, inactive users, refresh rotation, and logout idempotency using the existing async session factory boundary.
- [ ] Run the focused tests and observe failure from missing schemas/service.
- [ ] Implement normalization, repository queries, transaction boundaries, and `HTTPException`-independent domain errors that the router can map.
- [ ] Run the focused tests against a disposable test database setup; keep production code async.

### Task 4: Expose Auth Routes and Current-User Dependency

**Files:**
- Create: `backend/app/auth/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth_api.py`

**Interfaces:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `get_current_user` dependency for later protected routers.

- [ ] Write HTTP tests for status codes, response shape, Bearer parsing, `/me`, refresh rotation, and logout.
- [ ] Run the API tests and observe failure because routes are not registered.
- [ ] Register the router, inject `AsyncSession`, map domain errors to stable JSON error codes, and return `204` for logout.
- [ ] Run the API tests, then the complete backend test suite.

### Task 5: Validate Migration and Documentation

**Files:**
- Modify: `backend/app/models/user.py` only if the implementation needs a schema adjustment.
- Create: `backend/alembic/versions/0002_auth_session_metadata.py` only if model changes require it.
- Modify: `产品需求文档.md`
- Modify: `软件架构设计文档.md`
- Modify: `当前项目进度.md`

- [ ] Add a migration only for model changes required by the tested refresh-session contract.
- [ ] Run `alembic check`, `alembic upgrade head`, and a downgrade/upgrade cycle against local MySQL 3307 when a migration exists.
- [ ] Update PRD to state V0 email/password authentication and V2 third-party login.
- [ ] Update architecture API, security, token lifetime, and session storage sections.
- [ ] Update the progress document with completed files, test evidence, and remaining auth follow-ups.
- [ ] Run full verification: `pytest`, `ruff check backend`, `alembic check`, and `npm run build` in `frontend`.
