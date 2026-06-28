# 项目架构

## 运行结构

```text
Nginx / Vite
      |
      v
FastAPI API -> Service / Unit of Work -> Repository -> PostgreSQL
                    |
                    +-> StorageProvider -> 持久化图片卷
                    |
                    +-> ModelProvider -> placeholder / OpenAI-compatible 多模态模型
                    |
                    +-> SearchService -> 数据库搜索 / Meilisearch 派生索引
```

前端的图片、标签和 AI 状态逻辑位于 `features/`，认证位于 `lib/auth.tsx`，
管理员界面位于 `pages/AdminUsers/`。远程状态由 TanStack Query 管理，接口类型
由 FastAPI OpenAPI 生成。

## 强制边界

- API 层处理 HTTP、Cookie、CSRF、权限和错误映射。
- Service 层实现用例和事务，不允许导入 FastAPI。
- Repository 只查询、添加、更新和删除 ORM 对象，不允许提交事务。
- Unit of Work 是写事务的唯一提交入口。
- Model 不作为 HTTP 响应直接返回；Schema 使用 camelCase 输出。
- 客户端永远不能提交或读取服务器物理路径。
- Storage key 由后端生成，并在解析时限制在 storage root 内。
- 数据库结构禁止使用 `create_all()`，只能通过 Alembic migration 修改。
- AI 业务只依赖 `ModelProvider`；未配置 Provider 时必须失败，不能返回空结果冒充成功。
- AI 输出必须先经过 normalizer、Pydantic schema 和 taxonomy catalog 校验，才能写入业务数据。
- 人工业务标签与 AI 建议必须区分来源：`origin=manual` 或 `origin=ai`；AI 建议通过 `review_status=pending/accepted/rejected` 流转。
- 数据库是图片、标签、AI 分析和审核状态的事实源；Meilisearch 只是可重建的派生索引。
- Meilisearch 不可用时搜索必须降级到数据库路径，不能阻断上传、详情或基础搜索。

这些约束由 `backend/tests/test_architecture.py` 和 CI 检查。

## 图片生命周期

上传流程：

1. 流式写入 `.staging`，执行大小、像素总量和 Pillow 真实格式校验。
2. 同步生成 JPEG 缩略图。
3. 创建数据库对象并 flush。
4. 原子移动原图和缩略图。
5. 提交数据库；失败时回滚并清理文件。

删除流程：

1. 普通删除只设置 `deleted_at`，图片进入回收站。
2. 回收站图片可恢复。
3. 永久删除才移除数据库记录、原图和缩略图。

预览使用 `/content`，不记录下载；附件下载使用 `/download`，响应完成后增加计数。

## 会话与权限

- 密码使用 Argon2。
- 服务端只保存会话 token 的 SHA-256。
- 浏览器会话 Cookie 为 HttpOnly、SameSite=Lax；生产环境启用 Secure。
- 写请求必须同时通过受信 Origin、CSRF Cookie/Header 和角色校验。
- 停用账号或重置密码时删除该用户全部会话。
- 登录失败按账号与客户端 IP 持久化限流，过期 Session 在登录时清理。
- 登录、图片、标签和用户管理写入审计日志。
- 每个响应包含 request ID 与基础安全响应头。

## 数据与部署

- 部署数据库：PostgreSQL。
- 本地开发：SQLite 兼容模式。
- 图片：服务器持久化卷；未来通过 `StorageProvider` 接入对象存储。
- Docker Compose 包含 Nginx、FastAPI、PostgreSQL、可选 Meilisearch profile 和持久化 volume。
- Compose 内的 Nginx 只提供 HTTP，生产 HTTPS 由外层反向代理或负载均衡负责。
- `/health/live` 检查进程存活，`/health/ready` 同时检查数据库。

## 状态记录与决策

截至 2026-06-28：

- 本地开发链路使用 SQLite，后端测试、前端检查和浏览器回归已经跑通过。
- PostgreSQL Schema、Alembic migration、Dockerfile、Nginx、Compose 和可选 Meilisearch profile 已经完成。
- 后端支持 OpenAI-compatible 多模态模型；未配置模型时返回明确的 `503 provider_not_configured`。
- 模型 Provider 已配置时，上传成功后可自动排队 AI 分析；分析结果写入前经过 schema、normalizer 和 taxonomy 校验。
- 搜索已支持精准搜索与智能搜索手动切换；Meilisearch 是可选增强层，不是主数据源。
- 图片生命周期、人工标签/AI 建议审核、AI 分析持久化和搜索编排已经拆成独立服务边界。
- 业务意图话术位于 `taxonomy/business_intents.json`，稳定标签仍位于 `taxonomy/catalog.json`。
- 搜索评测资产位于 `taxonomy/search_eval_cases.json`，当前覆盖 50 条用例和全部二级业务标签。
- Docker 默认只启动 web、backend 和 postgres；Meilisearch profile 需要显式配置并启动。
- 本地继续开发不需要安装 Docker、Podman 或 PostgreSQL；服务器推荐仅安装 Docker Engine 与 Compose。
- PostgreSQL 使用 Compose 容器，不在宿主机重复安装；Podman 不在默认支持范围内。
- 生产部署是否完成，仍以目标服务器实际验收为准。

生产部署是否完成，以根目录 README 的“服务器上线验收清单”为唯一判定标准。
后续排查时先检查该清单，不要重复讨论已经由测试覆盖的本地代码问题。

## 下一轮决策

优先做能让项目进入真实使用闭环的事情：

1. 服务器上线验收，确认部署、持久化、权限和备份恢复。
2. 用真实图片和 50 条搜索评测用例记录搜索质量。
3. 如果上传和模型分析变慢，再把 AI 分析从 `BackgroundTasks` 升级为独立 worker。
4. 在继续新增标签、AI 和审核功能前，优先清理前端旧类型、文档漂移和搜索排序服务重量。
