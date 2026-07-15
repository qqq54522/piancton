# Python 后端

FastAPI 应用使用 API、Service、Repository、Model/Database 分层。数据库结构只能通过 Alembic 修改。

> 当前业务模型和阶段状态以项目根目录的 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为准。旧图片直挂标签、旧场景/功能分类和搜索请求模式已在 Phase 6 下线。

## 常用命令

```bash
source .venv/bin/activate
alembic upgrade head
python -m scripts.create_admin admin 'strong-password'
python -m scripts.seed_taxonomy
uvicorn app.main:app --reload --port 8000
pytest -q
ruff check app tests
pyright
```

根目录也提供统一检查与打包入口：

```bash
make check
make docker-build
make docker-up
```

`seed_taxonomy` 同步六大体系稳定节点，并幂等初始化当前业务概念、概念体系关系、概念搜索表达和概念关系。图片不再直接挂固定标签；图片与业务概念的负责人确认事实保存在素材组关系中。

- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

## 权限

| 能力 | business | designer | admin |
|---|---:|---:|---:|
| 浏览、搜索、预览、下载 | ✓ | ✓ | ✓ |
| 上传、维护素材版本和概念关系 |  | ✓ | ✓ |
| AI 操作 |  | ✓ | ✓ |
| 用户管理 |  |  | ✓ |
| 审计日志 |  |  | ✓ |

前端权限仅控制显示，所有写权限由后端强制执行。

系统提供 `/health/live` 和 `/health/ready`，并为响应附加 request ID 与安全响应头。
图片删除默认进入回收站，只有永久删除才会清理原图和缩略图。

## AI Provider

后端支持 `MODEL_PROVIDER=openai_compatible`，通过 OpenAI-compatible
`/chat/completions` 接口调用多模态模型。必填环境变量：

- `MODEL_BASE_URL`
- `MODEL_API_KEY`
- `MODEL_NAME`
- `MODEL_TIMEOUT_SECONDS`，默认 120 秒

模型必须能处理图片输入，并稳定返回 JSON 对象。业务层只依赖
`ModelProvider` 协议；新增或替换模型时，只改 `app/ai` 适配器。

## 搜索后端

默认 `SEARCH_BACKEND=database`，统一搜索仍执行数据库概念/短语召回。可设置
`SEARCH_BACKEND=meilisearch` 启用 Meilisearch 关键词增强分支：

- `MEILISEARCH_URL`，例如 `http://meilisearch:7700`
- `MEILISEARCH_API_KEY`，可选
- `MEILISEARCH_INDEX`，默认 `images`
- `SEARCH_TIMEOUT_SECONDS`，默认 2 秒

在线搜索由一条限时异步编排统一执行：数据库、Meilisearch、Embedding 和复杂查询理解按配置并行运行，候选融合后最多调用一次 Reranker。任一外部分支不可用或超时时，接口使用已取得的候选返回，并通过诊断字段记录降级来源。

重建派生搜索索引：

```bash
python -m scripts.verify_search_index
python -m scripts.rebuild_search_index --dry-run
python -m scripts.rebuild_search_index
```

`verify_search_index` 使用临时 Meilisearch 索引验证真实索引写入和
SearchService 查询；`--dry-run` 只打印前几条搜索文档，不访问 Meilisearch。
正式验证和重建需要先配置 `MEILISEARCH_URL`。Meilisearch 永远是可重建派生索引，不是素材或业务概念的事实源。

Docker 默认不会配置 `MEILISEARCH_URL`，因此没有启用搜索 profile 时，上传和编辑
不会反复尝试同步一个不存在的搜索容器。启用 profile 时必须显式配置
`MEILISEARCH_URL=http://meilisearch:7700` 和匹配的 `MEILISEARCH_API_KEY`。
