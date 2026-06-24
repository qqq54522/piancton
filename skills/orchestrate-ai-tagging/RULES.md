# AI 自动打标编排 Skill

用途：串联图片识别、二级标签判断、校验和持久化。

## 流程

```text
local image
  -> ModelProvider
  -> observable content profile
  -> closed secondary-label classification
  -> Pydantic validation
  -> existing-tag matching
  -> transactional profile persistence
  -> API response
```

Trigger:

- Run automatically immediately after a successful upload when the provider is configured.
- Manual “重新分析” runs the exact same complete pipeline.
- Upload success and AI analysis failure must be reported separately; never claim that
  analysis succeeded when only the image upload succeeded.

Persist:

- image summary;
- open content tags with confidence and dimension;
- closed secondary categories with confidence and reason;
- optional matched manual tags.

Boundary:

- Manual hierarchy tags remain human-managed.
- Closed secondary matches are stored as AI automatic matches and must not silently
  create or overwrite manual hierarchy tags.

Failure rules:

- Unconfigured provider: HTTP 503 with a clear message.
- Invalid JSON/schema: no partial persistence.
- Model timeout: preserve prior profile.
- Unknown closed label: reject it.
- Empty analysis: treat as a failure, not a successful blank result.
