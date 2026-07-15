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
                    +-> SearchService -> 限时并行搜索编排
                                      -> 数据库概念/短语召回
                                      -> Meilisearch / Embedding / 查询理解
                                      -> 一次可选 Reranker
```

前端的图片、素材组和 AI 状态逻辑位于 `features/`，认证位于 `lib/auth.tsx`，
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
- 素材概念关系必须区分人工事实与 AI 建议：`origin=manual/ai`；AI 建议通过 `review_status=pending/accepted/rejected` 流转。
- 数据库是图片、业务概念、素材关系、AI 分析和审核状态的事实源；Meilisearch 只是可重建的派生索引。
- Meilisearch 不可用时搜索必须降级到数据库路径，不能阻断上传、详情或基础搜索。
- 普通业务用户只有一个搜索框；六大体系只有在用户显式选择时才是硬过滤。
- 外部搜索分支不得共享请求 SQLAlchemy Session；ORM 实体只由请求主会话水合。
- 候选融合后最多执行一次 Reranker，生成式图片摘要裁判不得回到在线链路。

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

## 当前状态记录

截至 2026-07-15：

- Phase 0～6 工程改造和旧职责清理完成，数据库 revision 为 `20260715_0014`。
- `tags` 只保留 6 个稳定体系节点；可变化业务语义位于 `business_concepts`、概念关系、概念搜索表达和素材概念关系。
- 首次上传自动建立素材组；主图可先发布，延展、备选和修订版本可后续追加。
- 图片客观语义使用 Semantic Profile V2 与 `content_tags`；AI 业务判断写入待审核素材概念关系建议。
- 在线搜索只有一条自动编排，不再向普通用户或 API 暴露搜索模式选择。
- 本地正式素材库当前为空；Phase 0/4 真实质量验收等待 3～6 张代表素材和 10～20 条真实查询重新建立。
- Phase 0～6 回滚提交已在 GitHub Actions 的 PostgreSQL 17 环境完成从零迁移、后端检查和前端检查。
- Docker Compose、Nginx、PostgreSQL 和可选 Meilisearch profile 已具备，但目标服务器生产验收、持久化和备份恢复仍未完成。

架构和业务阶段的唯一事实来源是 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`；部署是否完成以根目录 README 和 `docs/SERVER_DEPLOYMENT_CHECKLIST.md` 的实际勾选记录为准。

## 下一轮决策

优先做能让项目进入真实使用闭环的事情：

1. 从空库录入 3～6 张代表素材并完成负责人关系确认。
2. 绑定 10～20 条真实查询，重建 Phase 0/4 质量和延迟基线。
3. 启用需要的外部搜索增强并执行故障注入、P95 和派生索引重建验证。
4. 服务器上线验收，确认部署、持久化、权限和备份恢复。
5. 如果上传和模型分析明显变慢，再把 AI 分析从 `BackgroundTasks` 升级为独立 worker。
