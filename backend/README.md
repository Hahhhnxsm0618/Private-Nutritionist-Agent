# Nutrition Agent API

## Local development

```powershell
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`

## Database migrations

Run from this directory after MySQL is healthy:

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade base
uv run alembic upgrade head
```

The initial migration creates the foundation tables for users, sessions, health facts, conversations, messages, idempotency, and audit records. It does not manage the external Milvus instance.

Run tests from this directory:

```powershell
uv run --group dev python -m pytest -q
```
