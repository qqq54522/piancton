# 项目架构 Skill

用途：新增功能、重构或审查代码时，约束项目分层和依赖方向。

## 架构边界

```text
React client -> FastAPI route -> Service -> Repository -> SQLAlchemy model
                                  |
                                  +-> Storage
                                  +-> ModelProvider
```

- `backend/app/api`: transport only.
- `backend/app/schemas`: stable requests and responses.
- `backend/app/services`: business workflows and deterministic rules.
- `backend/app/repositories`: database reads and writes only.
- `backend/app/models`: persistence definitions only.
- `backend/app/ai`: vendor-neutral model boundary and adapters.
- `storage/images`: local image bytes.
- `skills`: capability instructions and rule references.

Allowed dependency direction is downward. Repositories must not import services;
providers must not own business taxonomies; frontend must not contain authoritative
classification rules.
