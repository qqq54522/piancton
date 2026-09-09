# 公司服务器首次部署准备

日期：2026-09-07。状态：本地部署准备版本；服务器应用尚未启动，生产验收未通过。

## 已确认范围

- 服务器：`118.196.150.130`，CentOS Stream 9 / x86_64；约 4 GB 内存，34 GB 可用磁盘。
- 用户截图确认 Git、Docker 29.8.0、Compose v5.5.1 安装完成，Docker active 且开机自启。
- 不迁移本地图片、旧账号、会话或 API 中心配置。服务器单独新建一个管理员。
- 使用仓库标签种子初始化六大体系和 16 个卖点；证明点、证据表达点目录由仓库知识文件提供。
- 复用现有 VikingDB 知识库；连接密钥在服务器单独配置，不复制本地环境文件，不运行知识库清空/重建脚本。

## 本轮部署修正

国内服务器构建时可直接在根目录 `.env` 覆盖完整镜像名与依赖源，无需修改 Dockerfile：

```env
POSTGRES_IMAGE=m.daocloud.io/docker.io/library/postgres:17-alpine
PYTHON_BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.12-slim
NODE_BASE_IMAGE=m.daocloud.io/docker.io/library/node:22-alpine
NGINX_BASE_IMAGE=m.daocloud.io/docker.io/library/nginx:1.27-alpine
MEILISEARCH_IMAGE=m.daocloud.io/docker.io/getmeili/meilisearch:v1.13
PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
```

这七项只影响拉取和构建来源，不改数据库、图片卷、业务数据或运行时 API 配置。

- Compose 显式传入 `.env.docker.example` 的全部 VikingDB 参数。
- `.dockerignore` 排除 `backend/.env.*`，仅保留示例文件，防止本地 VikingDB 配置进入镜像。
- 服务设置 `restart: unless-stopped`，支持服务器重启后自动恢复。
- 不修改数据库迁移、标签含义或搜索规则。

## 本地验证

- 前端 TypeScript、ESLint、Vitest（13 文件 / 54 测试）和生产构建通过。
- Docker 后端镜像构建通过；未重启本地现有服务。
- 无网络临时容器中，空 SQLite 数据库迁移至 `20260829_0033`，种子首次创建 6 个体系、16 个卖点；第二次创建和更新均为 0。
- 空库 `users/images/model_api_credentials` 均为 0；镜像不存在 `/app/backend/.env.vikingdb.local`。
- 同一新镜像后端全量测试：364 passed、21 failed、4 skipped。失败涉及退役图片分析契约、旧 Phase 4 路由预期及搜索编排行数守卫；未通过删除测试或恢复退役功能掩盖失败。
- Ruff 报告 44 项，集中在未提交的微调数据生成脚本；项目 Pyright 报告 34 errors / 1 warning。旧本地 Python 3.9 无法加载当前部分接口，部署验证使用镜像 Python 3.12。
- 本版本是可追溯部署准备快照，不是全部工程检查通过的生产发布。

## 服务器后续步骤

1. 拉取部署准备分支，并核对本次交付的 Git commit。
2. 在新的部署目录复制 `.env.docker.example` 为 `.env`，生成独立数据库密码。
3. 配置访问地址。临时 IP HTTP 验证使用 `CORS_ORIGINS=http://118.196.150.130` 和 `SESSION_COOKIE_SECURE=false`；正式 HTTPS 上线时改成最终域名及 `true`。
4. API 中心相关密钥保持为空。若尚未配置 VikingDB，先保持开关关闭，不能宣称自由搜索已接通。
5. 复用向量库时单独填写 `VIKINGDB_API_KEY`、实际 collection/index；开启 `VIKINGDB_ENABLED=true`、`VIKINGDB_KNOWLEDGE_ROUTER_ENABLED=true`，设置 `VIKINGDB_SKILL_BACKUP_ENABLED=false`。不要执行 `reset_vikingdb_knowledge_index` 或重建已有知识库。
6. 执行 `docker compose up --build -d`。容器入口自动执行迁移和标签种子，无须导入旧数据库。
7. 单独创建管理员，检查登录、标签选择、上传、持久化和向量连接；服务器 PostgreSQL 初始化必须现场验证。
8. 在解决遗留工程检查并完成 HTTPS、备份恢复及功能验收后，才更新 `SERVER_DEPLOYMENT_CHECKLIST.md` 为生产验收通过。

若 Docker Hub 镜像拉取失败，先解决镜像源连通性；安装 Docker 的 yum 镜像源并不自动加速容器镜像下载。
