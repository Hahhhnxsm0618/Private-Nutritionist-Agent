# 营养师智能体

404 page not foundV0 工程骨架：Vue 3 + FastAPI + MySQL 8.0 + Milvus + LangChain。

## 目录

- `frontend/`：Vue Web 应用
- `backend/`：FastAPI 服务
- `docker-compose.yml`：MySQL 8.0 本地依赖；Milvus 复用外部已运行实例
- `产品需求文档.md`：产品需求与验收标准
- `软件架构设计文档.md`：架构、技术栈和接口边界

## 启动基础设施

```powershell
Copy-Item .env.example .env
docker compose up -d
```

项目 Compose 只启动 MySQL，默认映射到 `127.0.0.1:3307`，避免与本机已有的 MySQL `3306` 端口冲突。Milvus 复用 `D:\docs\milvus` 中已运行的实例，地址为 `127.0.0.1:19530`。

## 启动后端

```powershell
Set-Location backend
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
```

健康检查：`http://localhost:8000/health`

## 启动前端

```powershell
Set-Location frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## 测试和构建

```powershell
Set-Location backend
uv run --group dev python -m pytest -q

Set-Location ..\frontend
npm run build
```
