# 营养师智能体项目骨架实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可启动、可测试的 Vue + FastAPI + MySQL + Milvus V0 工程骨架。

**Architecture:** 前后端分离的模块化单体。后端先提供 `/health`，前端提供可访问的启动页；MySQL 和 Milvus 通过 Docker Compose 提供本地依赖，真实 Agent 和业务模块留到后续任务。

**Tech Stack:** Vue 3、TypeScript、Vite、Vue Router、Pinia、`@tanstack/vue-query`、Python、FastAPI、Pydantic、pytest、HTTPX、MySQL 8.0、Milvus、Docker Compose、uv、Ruff。

**Spec:** `软件架构设计文档.md`、`产品需求文档.md`

## Global Constraints

- V0 到第一版生产环境使用 MySQL 8.0，不默认迁移 PostgreSQL。
- 前端服务端状态使用 `@tanstack/vue-query`，本地 UI 状态使用 Pinia。
- 安全规则和业务流程由 Python 服务控制，暂不使用 CrewAI 作为核心编排。
- 本轮只建立骨架，不接入真实模型、RAG、登录和业务数据库表。
- 所有新增前端组件使用语义 HTML、可见焦点和键盘可操作控件。

---

### Task 1: FastAPI health endpoint

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/pyproject.toml`
- Create: `backend/README.md`

**Interfaces:**
- Produces: `GET /health` returning `{"status": "ok", "service": "nutrition-agent-api"}` with HTTP 200.

- [x] Write the health endpoint test in `backend/tests/test_health.py` using FastAPI `TestClient`.
- [x] Add the minimal FastAPI application and health route.
- [x] Add backend dependencies and pytest configuration to `backend/pyproject.toml`.
- [x] Run the backend test suite from `backend`; it passes.

### Task 2: Frontend shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`
- Create: `frontend/README.md`

**Interfaces:**
- Produces: a Vue page with a named main heading, service status placeholder, and keyboard-visible primary action.

- [x] Add the minimal Vite/Vue package configuration.
- [x] Add `App.vue` with semantic `main`, heading, status text, and a button with visible focus state.
- [x] Add responsive base styles without introducing application business behavior.
- [x] Run `npm install` and `npm run build` from `frontend`.

### Task 3: Local infrastructure and environment templates

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/.env.example`
- Create: `frontend/.env.example`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Produces: MySQL 8.0 and Milvus local services with explicit ports, health checks, named volumes, and documented startup commands.

- [x] Define MySQL and Milvus services without embedding application secrets.
- [x] Add environment variable names for API URL, database URL, Milvus URI, model provider, and model name.
- [x] Document install, dependency, test, frontend, backend, and infrastructure commands.
- [x] Run `docker compose config` and confirm the Compose file is valid.

### Task 4: Skeleton verification

**Files:**
- Modify: `当前项目进度.md`

- [x] Run backend tests, frontend build, and Compose validation.
- [x] Record exact verified results and the Docker external-service limitation in the progress document.
- [x] Confirm no real model keys or secrets were added.
