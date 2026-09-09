# 数据库基础层设计

**日期**：2026-09-09  
**适用范围**：V0 第一批数据库基础层  
**状态**：已实现并完成本地 MySQL 验证

## 目标

使用 MySQL 8.0、SQLAlchemy 2 和 Alembic 建立可迁移、可测试的基础数据层，先支撑认证、用户隔离、健康档案、对话、幂等和审计，再按业务闭环增加饮食记录、目标、方案和知识库表。

## 技术约束

- 使用项目 Docker Compose 提供的 MySQL 8.0，宿主机映射端口为 `3307`。
- Milvus 继续复用 `D:\docs\milvus` 的外部实例，不在关系数据库迁移中管理。
- 使用 SQLAlchemy 2 async engine 和 `async_sessionmaker`。
- 使用 Alembic 管理迁移，模型元数据作为迁移生成和测试的来源。
- 主键使用 UUID 字符串，便于 API、日志和跨服务标识；不使用自增整数暴露资源顺序。
- 时间统一保存为 UTC `DATETIME(6)`。
- 状态字段使用字符串存储，由 Python Enum/Pydantic Schema 校验，避免 MySQL 原生 ENUM 降低迁移灵活性。
- 可变的半结构化字段使用 MySQL JSON；敏感原始文本不进入日志和非必要的审计字段。

## 第一批表

| 表 | 用途 | 关键约束 |
|---|---|---|
| `users` | 账号、角色和用户状态 | `email` 唯一；只保存密码哈希 |
| `auth_sessions` | 登录会话 | 令牌只保存哈希；支持过期和撤销 |
| `health_profiles` | 基础健康档案 | 与用户一对一；记忆开关明确保存 |
| `health_facts` | 可授权的健康事实 | 必须包含 `user_id`、来源、状态和用途授权 |
| `consents` | 授权记录 | 保存授权类型、版本、同意/撤回时间 |
| `conversations` | 对话会话 | 必须归属用户；记录最近活动时间 |
| `messages` | 用户和助手消息 | 记录角色、状态、风险等级、请求标识和 `trace_id` |
| `idempotency_keys` | 写请求幂等 | 用户、路由和请求键联合唯一 |
| `audit_logs` | 敏感操作审计 | 记录操作者、动作、资源和结果，不保存不必要原文 |

## 领域状态

- 健康事实：`confirmed`、`inferred`、`pending`、`expired`。
- 消息：`pending`、`streaming`、`succeeded`、`failed`。
- 用户和会话状态：使用有限字符串集合，由领域层校验。
- 只有 `confirmed` 且授权有效的健康事实可进入长期个性化上下文。
- 只有 `succeeded` 的助手消息进入正常对话历史。

## 关系与隔离

- 所有用户资源直接包含 `user_id`，仓储层默认要求用户范围参数。
- `users` 一对一 `health_profiles`，一对多 `auth_sessions`、`health_facts`、`consents`、`conversations`、`idempotency_keys` 和 `audit_logs`。
- `conversations` 一对多 `messages`。
- 外键使用显式约束；删除策略由应用服务控制，第一批迁移不使用级联删除来隐藏隐私删除流程。
- 业务查询禁止只依赖 URL 中的资源 ID，必须同时校验当前用户归属。

## 迁移和测试验收

- Alembic 初始迁移可以在空 MySQL 数据库中执行。
- 迁移回滚可以删除第一批表，不删除项目外部数据。
- SQLAlchemy 元数据能被测试导入，模型关系和唯一约束可检查。
- 使用真实本地 MySQL 执行一次迁移和回滚/重建验证。
- 后续业务表单独迁移，不把饮食、方案和知识库业务字段提前塞入基础迁移。
