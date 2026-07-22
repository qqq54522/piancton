# 项目架构运行规则

用途：新增功能、重构或审查代码时，约束项目分层和依赖方向。

## 架构边界

```text
React client -> FastAPI route -> Service -> Repository -> SQLAlchemy model
                                  |
                                  +-> Domain policy
                                  +-> Storage
                                  +-> ModelProvider
                                  +-> Search boundary services
```

- `backend/app/api`: transport only.
- `backend/app/schemas`: stable requests and responses.
- `backend/app/services`: business workflows and deterministic rules.
- `backend/app/domain`: pure business policies, data structures and evaluation logic.
- `backend/app/repositories`: database reads and writes only.
- `backend/app/models`: persistence definitions only.
- `backend/app/ai`: vendor-neutral model boundary and adapters.
- `storage/images`: local image bytes.
- `skills`: capability instructions and rule references.

Allowed dependency direction is downward. Repositories must not import services;
providers must not own business taxonomies; frontend must not contain authoritative
classification rules.

Search assembly must remain split: `SearchService` wires dependencies,
`AsyncSearchOrchestrator` sequences the pipeline, external branches own timeouts and
hydration, and the rerank coordinator owns the single optional Reranker call.
