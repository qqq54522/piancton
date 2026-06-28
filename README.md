# 标签图片仓库

面向设计师与业务团队的内部图片素材仓库。设计师维护图片、标签和分类，业务人员通过标签与关键词检索并下载素材，管理员负责内测账号。

## 当前能力

- HttpOnly Cookie 会话、CSRF 防护和后端角色权限
- 图片安全上传、真实格式校验、预览与下载计数分离
- 自动缩略图、图片回收站与永久删除
- 标签树、允许打标标签必选、同级名称唯一、分类、稳定游标分页和多标签 AND 筛选
- PostgreSQL + Alembic，开发环境也可使用 SQLite
- 本地持久化图片卷，可替换 Storage Provider
- AI Provider 稳定接口；未配置时明确返回 `503 provider_not_configured`
- 已支持 OpenAI-compatible 多模态模型接入，API Key 只放后端环境变量
- 模型 Provider 已配置时，上传成功后自动排队 AI 分析；生成 18–22 个中文隐形内容标签
- AI 自动匹配只使用封闭的 16 个业务标签，不修改人工标签树
- React、TanStack Query、OpenAPI TypeScript 类型和管理员页面
- 登录失败限流、结构化 request ID、安全响应头和操作审计

## 当前状态与后续工作

代码层面的内测版优化、六阶段标签/AI/搜索改造和第一轮小清理已经完成。
当前本地检查结果：

- 后端 pytest：84 项通过
- Ruff、Pyright：通过
- 前端 TypeScript、Vitest、生产构建：通过
- 搜索评测资产：50 条用例通过结构校验
- 服务器生产验收仍以本文件后续清单为准

剩余工作不是重复改基础代码，而是在目标服务器执行生产环境验收，并用真实素材库持续记录搜索质量：

1. 在服务器安装 Docker Engine 和 Docker Compose。
2. 配置生产域名、HTTPS 和 `.env`。
3. 启动 Nginx、FastAPI、PostgreSQL 和持久化卷。
4. 执行 Alembic migration 并创建首位管理员。
5. 验证登录、权限、上传、预览、下载和用户管理。
6. 重启容器，确认数据库和图片仍然保留。
7. 配置并演练 PostgreSQL 与图片卷的备份恢复。

在以上服务器验收完成前，不要把项目标记为“生产部署已验证”。

## 本地开发

后端默认使用 `data/piancton.db`：

本地继续开发不需要安装 Docker、Podman 或 PostgreSQL。三者也不需要同时安装。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.create_admin admin 'replace-with-a-strong-password'
python -m scripts.seed_taxonomy
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd client
npm install
npm run dev
```

统一检查入口：

```bash
make check
```

API 变化后，在后端运行期间执行：

```bash
cd client
npm run generate:api
```

## AI 模型配置

第一版推荐只接一个支持图片输入和 JSON 输出的多模态模型。后端通过
OpenAI-compatible Chat Completions 协议调用，前端永远不接触 API Key。

本地开发在 `backend/.env` 中配置：

```env
MODEL_PROVIDER=openai_compatible
MODEL_BASE_URL=https://api.example.com/v1
MODEL_API_KEY=replace-with-your-secret-key
MODEL_NAME=your-vision-model
MODEL_TIMEOUT_SECONDS=120
```

服务器 Docker 部署在项目根目录 `.env` 中配置同名变量。若未配置完整，
`/api/ai/*` 写接口会稳定返回 `503 provider_not_configured`，不会假装成功。

如果 API Key 曾经粘贴到聊天、截图或公共文档里，上线前请在模型平台重新生成
一个新 Key，并废弃旧 Key。

## Docker 部署

推荐的服务器方案是只安装 Docker Engine 和 Docker Compose。PostgreSQL 由
`docker-compose.yml` 自动启动，不需要在服务器宿主机额外安装 PostgreSQL；
Podman 是 Docker 的替代方案，本项目默认不使用。

Compose 内置的 Nginx 监听 HTTP。生产域名的 HTTPS 证书应由服务器外层反向代理
或云负载均衡终止，再转发到 `WEB_PORT`；不要把当前 Nginx 配置误认为已经包含证书。

```bash
cp .env.docker.example .env
# 修改数据库密码、CORS_ORIGINS、Cookie 和可选模型配置
# 如需启用 AI，同时配置 MODEL_PROVIDER、MODEL_BASE_URL、MODEL_API_KEY、MODEL_NAME
docker compose up --build -d
docker compose exec backend python -m scripts.create_admin admin 'replace-with-a-strong-password'
docker compose exec backend python -m scripts.seed_taxonomy
```

生产 HTTPS 环境必须设置 `SESSION_COOKIE_SECURE=true`，并把 `CORS_ORIGINS`
设置为最终 HTTPS 域名，例如 `https://images.example.com`。

如果 Docker Hub 拉取超时，可以优先使用云厂商提供的 Docker 镜像加速器。项目也支持在
`.env` 中覆盖基础镜像完整名称：

```env
POSTGRES_IMAGE=你的镜像源/library/postgres:17-alpine
PYTHON_BASE_IMAGE=你的镜像源/library/python:3.12-slim
NODE_BASE_IMAGE=你的镜像源/library/node:22-alpine
NGINX_BASE_IMAGE=你的镜像源/library/nginx:1.27-alpine
MEILISEARCH_IMAGE=你的镜像源/getmeili/meilisearch:v1.13
```

不填这些变量时，仍使用 Docker Hub 默认镜像。

如需验证 Meilisearch 影子搜索，先在 `.env` 中设置：

```env
SEARCH_BACKEND=meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_API_KEY=replace-with-a-search-master-key
```

再启动可选搜索 profile 并重建派生索引：

```bash
docker compose --profile search up --build -d
docker compose exec backend python -m scripts.verify_search_index
docker compose exec backend python -m scripts.rebuild_search_index
```

`verify_search_index` 会创建临时索引、写入搜索文档、通过后端 SearchService
执行真实 Meilisearch 查询，并在成功后清理临时索引。它通过后，再重建正式
`images` 索引。Meilisearch 是可重建的搜索索引，不是主数据库。它不可用时
后端会自动降级到数据库模糊搜索。

## 服务器上线验收清单

- [ ] `.env` 中已替换默认 PostgreSQL 密码
- [ ] `CORS_ORIGINS` 是最终 HTTPS 域名
- [ ] `SESSION_COOKIE_SECURE=true`
- [ ] 反向代理已配置有效 HTTPS 证书
- [ ] `docker compose up --build -d` 成功
- [ ] `docker compose ps` 中三个服务均健康
- [ ] Alembic 已升级到最新 revision
- [ ] 首位管理员已创建且初始密码已修改
- [ ] 六大体系与二级标签已通过 `python -m scripts.seed_taxonomy` 初始化
- [ ] 上传和编辑图片时至少选择一个已启用且允许打标的标签
- [ ] business 无法调用写接口
- [ ] designer 可上传和维护素材，但不能管理用户
- [ ] admin 可管理用户
- [ ] 预览不增加下载数，下载只增加一次
- [ ] 非图片、伪造图片和超限图片会被拒绝
- [ ] 超像素图片会被拒绝，列表使用缩略图
- [ ] 删除进入回收站，恢复和永久删除均正常
- [ ] 登录限流、安全响应头和 request ID 正常
- [ ] 管理员可以查看审计日志
- [ ] 容器重启后用户、标签、图片和下载数仍然存在
- [ ] PostgreSQL 与图片卷已建立定时备份
- [ ] 已实际完成一次备份恢复演练

每次部署或重大升级都按此清单复验，不再从聊天记录中重新整理。

架构与边界规则见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 当前文档与优化记录

项目文档只保留当前可执行信息，以及用于追踪未来计划和已完成改造的优化记录：

- [后续开发核心护栏](docs/DEVELOPMENT_GUARDRAILS.md)
- [架构与边界规则](docs/ARCHITECTURE.md)
- [搜索模式、大模型理解与图片语义补标](docs/SEARCH_MODES_AND_AI.md)
- [项目改造与意图识别施工入口](docs/REFACTOR_AND_INTENT_EXECUTION_PLAN.md)
- [搜索业务话术词库与意图簇映射](docs/SEARCH_BUSINESS_INTENT_MAP.md)
- [标签系统完善与 AI 打标改造方案](docs/TAGGING_SYSTEM_IMPROVEMENT_PLAN.md)
- [服务器部署验收清单](docs/SERVER_DEPLOYMENT_CHECKLIST.md)
- [搜索引擎选型决策](docs/adr/0001-search-engine.md)
- [项目优化记录与后续计划](docs/OPTIMIZATION_PLAN.md)

第一轮已实施目录治理、稳定业务编码、人工/AI 标签来源拆分、旧图人工标签回填、
分析批次记录、数据库确定性搜索词扩展、精准/智能搜索手动切换、搜索意图理解接入、
Meilisearch 可选降级层、搜索索引增量同步和重建脚本。业务搜索没有强制切换为
Meilisearch 单一路径，也不要求额外采购 OCR、Embedding 或 Reranker API。

打包优化入口：

- `make check`：后端测试、Ruff、Pyright、前端类型检查、前端测试和生产构建。
- `make docker-build`：只构建 Compose 镜像。
- `make docker-up`：启动默认的 web、backend、postgres。
- `make docker-up-search`：同时启动可选 Meilisearch profile。
