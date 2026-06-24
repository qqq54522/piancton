# Python 后端

FastAPI 应用使用 API、Service、Repository、Model/Database 分层。数据库结构只能通过 Alembic 修改。

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

`seed_taxonomy` 除了同步六大体系目录，也会把旧的 `image_tags` 关系回填为
`image_business_labels` 中的人工主/附加业务标签。标准体系根节点等不可打标标签
不会被回填。

- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

## 权限

| 能力 | business | designer | admin |
|---|---:|---:|---:|
| 浏览、搜索、预览、下载 | ✓ | ✓ | ✓ |
| 上传、编辑图片和标签 |  | ✓ | ✓ |
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

默认 `SEARCH_BACKEND=database`，使用本地数据库模糊搜索。可设置
`SEARCH_BACKEND=meilisearch` 启用影子搜索：

- `MEILISEARCH_URL`，例如 `http://meilisearch:7700`
- `MEILISEARCH_API_KEY`，可选
- `MEILISEARCH_INDEX`，默认 `images`
- `SEARCH_TIMEOUT_SECONDS`，默认 2 秒

Meilisearch 不可用或返回异常时，接口会自动降级到数据库搜索，并在响应中
返回 `fallback=true` 和 `fallbackReason`。

重建派生搜索索引：

```bash
python -m scripts.verify_search_index
python -m scripts.rebuild_search_index --dry-run
python -m scripts.rebuild_search_index
```

`verify_search_index` 使用临时 Meilisearch 索引验证真实索引写入和
SearchService 查询；`--dry-run` 只打印前几条搜索文档，不访问 Meilisearch。
正式验证和重建需要先配置 `MEILISEARCH_URL`。
