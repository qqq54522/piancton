# 卖点智库

面向设计师与业务团队的内部卖点素材智库。设计师维护主图、延展版本、业务概念关系和素材独有搜索语，业务人员通过一个搜索框检索并下载素材，管理员负责账号、审计和搜索运营。

> 当前项目状态以 [图片搜索系统改造总纲](docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md) 为唯一事实来源。Phase 0～6 工程改造已完成，当前本地库已有 40 个素材组和 40 张图片；后续继续补齐真实业务话术、画面级金标准和证明点细标。

## 当前能力

- HttpOnly Cookie 会话、CSRF 防护和后端角色权限
- 图片安全上传、真实格式校验、预览与下载计数分离
- 自动缩略图、图片回收站与永久删除
- 六大体系稳定地图、版本化业务概念及多对多素材关系
- 主图、延展图、备选图、修订版和素材组级去重展示；尺寸延展只识别尺寸并继承主图语义，不重复 AI 分析；同组版本不重复进入相关素材，非主图版本可单独移入回收站并恢复
- PostgreSQL + Alembic，开发环境也可使用 SQLite
- 本地持久化图片卷，可替换 Storage Provider
- 在线 AI 搜索、推荐和 Agent 问答统一通过火山 AI Search；未配置时使用本地业务目录和数据库降级
- 管理员可查看按用户、今日和区间聚合的登录、访问与下载使用量
- 图片上传保留人工维护和已存语义；上传成功后不再自动调用独立图片分析模型
- AI 建议与负责人确认严格区分来源和审核状态，不覆盖人工确认事实
- 卖点公共话术集中管理并由关联素材继承，单张图片只维护独有画面和场景说法
- 一个业务搜索框、六大体系可选筛选；AI Search 判断卖点与推荐，本地人工 accepted 关系约束图库，数据库/Meilisearch 提供可降级召回；结果仍可按卖点、渠道、画面风格和场景图精细筛选
- React、TanStack Query、OpenAPI TypeScript 类型和管理员页面
- 登录失败限流、结构化 request ID、安全响应头和操作审计

## 当前状态与后续工作

Phase 0～6 工程改造和旧职责清理已经完成。当前本地素材库已有 40 个素材组、40 张图片、16 个业务概念和 55 条人工 accepted 关系；下一步继续用真实业务话术、画面级金标准和证明点细标重建搜索基线。
当前本地检查结果：

- 后端 pytest：当前定向回归已通过；完整回归按总纲最新记录为准
- 修改范围 Ruff 通过；全量 Pyright 尚有历史类型错误，以项目日志 D349 记录为准
- 前端 TypeScript、ESLint、Vitest、生产构建：通过
- 搜索评测资产：50 条用例通过结构校验
- PostgreSQL 17 CI：Phase 0～6 回滚提交已通过从零迁移和全量检查
- 服务器生产验收仍以本文件后续清单为准

剩余工作不是重复改基础代码，而是建立真实素材闭环并完成生产环境验收：

1. 继续确认“主要表达/可以支持/不适用”关系，并补齐证明点细标。
2. 建立真实查询绑定，重新生成 Phase 0/4 报告。
3. 验证 AI Search 搜索、推荐与 Agent 的真实效果，完成故障注入和 P95 压测。
4. 在目标服务器配置域名、HTTPS、PostgreSQL 和持久化卷。
5. 验证权限、上传、搜索、预览、下载和反馈闭环。
6. 配置并演练 PostgreSQL 与图片卷的备份恢复。

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

## AI Search 配置

Docker 部署从 `.env.docker.example` 复制为根目录 `.env`；直接启动后端从
`backend/.env.example` 复制为 `backend/.env`。在线 AI 只使用火山 AI Search：

```env
AI_SEARCH_ENABLED=true
AI_SEARCH_CHAT_ENABLED=true
AI_SEARCH_BASE_URL=https://aisearch.cn-beijing.volces.com
AI_SEARCH_API_KEY=replace-with-your-secret-key
AI_SEARCH_APPLICATION_ID=your-application-id
AI_SEARCH_DATASET_ID=your-image-dataset-id
AI_SEARCH_CHAT_DATASET_IDS=your-knowledge-dataset-id,your-image-dataset-id
```

知识库问答需把知识数据集 ID 放入 `AI_SEARCH_CHAT_DATASET_IDS`；只填写图片数据集
不会自动连接另一份知识库。推荐和行为上报按环境示例中的 `AI_SEARCH_RECOMMEND_*`
与 `AI_SEARCH_BEHAVIOR_*` 配置。API 中心、自动模型调度和 `/api/ai/*` 接口已退出运行时；
旧模型密钥不再参与搜索、Agent 或上传。真实密钥仅放在 Git 忽略的环境文件中。

## Docker 部署

2026-09-07 公司服务器空库部署范围、验证结果和待办见
[公司服务器部署准备](docs/COMPANY_SERVER_DEPLOYMENT_2026-09-07.md)。

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

如需启用 Meilisearch 关键词增强分支，先在 `.env` 中设置：

```env
SEARCH_BACKEND=meilisearch
COMPOSE_PROFILES=search
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
`images` 索引。Meilisearch 是可重建的派生索引，不是主数据库；不可用或超时时，统一搜索编排继续使用数据库概念/短语召回及其他已配置分支。

## 服务器上线验收清单

- [ ] `.env` 中已替换默认 PostgreSQL 密码
- [ ] `CORS_ORIGINS` 是最终 HTTPS 域名
- [ ] `SESSION_COOKIE_SECURE=true`
- [ ] 反向代理已配置有效 HTTPS 证书
- [ ] `docker compose up --build -d` 成功
- [ ] `docker compose ps` 中三个服务均健康
- [ ] Alembic 已升级到最新 revision
- [ ] 首位管理员已创建且初始密码已修改
- [ ] 六大体系与业务概念种子已通过 `python -m scripts.seed_taxonomy` 初始化
- [ ] 首次上传不要求业务概念或延展尺寸，上传后会自动建立素材组
- [ ] 设计师可确认业务概念关系、追加延展版本、将非主图版本移入回收站并替换主图
- [ ] 尺寸/渠道延展上传后不产生 AI 分析任务，也不改变主图关系或素材话术
- [ ] 业务用户只看到一个搜索框，六大体系筛选为可选项
- [ ] business 无法调用写接口
- [ ] designer 可上传和维护素材，但不能管理用户
- [ ] admin 可管理用户
- [ ] 预览不增加下载数，下载只增加一次
- [ ] 非图片、伪造图片和超限图片会被拒绝
- [ ] 超像素图片会被拒绝，列表使用缩略图
- [ ] 删除进入回收站，恢复和永久删除均正常
- [ ] 登录限流、安全响应头和 request ID 正常
- [ ] 管理员可以查看审计日志
- [ ] 容器重启后用户、体系、业务概念、素材组、图片和下载数仍然存在
- [ ] PostgreSQL 与图片卷已建立定时备份
- [ ] 已实际完成一次备份恢复演练

每次部署或重大升级都按此清单复验，不再从聊天记录中重新整理。

架构与边界规则见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 当前文档与优化记录

当前执行文档：

- [图片搜索系统改造总纲（唯一事实来源）](docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md)
- [图片搜索改造项目日志](docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md)
- [后续开发核心护栏](docs/DEVELOPMENT_GUARDRAILS.md)
- [架构与边界规则](docs/ARCHITECTURE.md)
- [统一搜索、AI 理解与图片语义分析](docs/SEARCH_MODES_AND_AI.md)
- [服务器部署验收清单](docs/SERVER_DEPLOYMENT_CHECKLIST.md)
- [搜索引擎选型决策](docs/adr/0001-search-engine.md)

历史施工和业务来源资料仍保留在 `docs/`，但文件顶部必须标记“历史文档说明”；历史内容不能覆盖总纲中的当前状态。

打包优化入口：

- `make check`：后端测试、Ruff、Pyright、前端类型检查、前端测试和生产构建。
- `make docker-build`：只构建 Compose 镜像。
- `make docker-up`：启动默认的 web、backend、postgres。
- `make docker-up-search`：同时启动可选 Meilisearch profile。
