# 项目架构运行规则

用途：新增功能、重构或审查代码时，约束项目分层和依赖方向。

## 架构边界

```text
React client -> FastAPI route -> Service -> Repository -> SQLAlchemy model
                                  |
                                  +-> Domain policy
                                  +-> Storage
                                  +-> Viking AI Search client
                                  +-> Search boundary services
```

- `backend/app/api`: transport only.
- `backend/app/schemas`: stable requests and responses.
- `backend/app/services`: business workflows and deterministic rules.
- `backend/app/domain`: pure business policies, data structures and evaluation logic.
- `backend/app/repositories`: database reads and writes only.
- `backend/app/models`: persistence definitions only.
- `backend/app/ai`: historical contracts for compatibility; no current Provider factory.
- `storage/images`: local image bytes.
- `skills`: capability instructions and rule references.

Allowed dependency direction is downward. Repositories must not import services;
AI Search clients must not own business taxonomies; frontend must not contain authoritative
classification rules.

Online AI calls go only through `VolcAiSearchClient`. Agent uses its `chat_search`
with the current knowledge and image datasets. Search may use a bounded local
deterministic fallback, but must not initialize another model, VikingDB router,
Embedding client, Reranker, or API Center scheduler.
