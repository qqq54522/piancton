# 火山 AI Search 行为闭环上线说明

Piancton 只会把**业务端账号**在首页搜索结果和 Agent 推荐图片上的真实行为写入本地 outbox，再由后台任务写入火山 AI Search 用户行为数据集。管理员和设计师的操作仍保留在本地运营日志中，但不会进入外部行为数据集。外部网络短暂失败只会把事件标为 `failed`，后续周期会继续重试。

## 同一 AI Search 应用的搜、推、问

现有物品数据集、知识数据集和用户行为数据集保持不变。首页普通搜索继续调用当前应用搜索场景；搜索框推荐词调用该场景下的 `query_recommendation`；Agent 新会话调用同一应用的 `opening_remarks`，正式对话继续调用 `chat_search`。控制台配置的开场白、推荐问题或推荐素材不可用时，Piancton 分别回退本地开场内容、静态搜索占位和既有 Agent 兜底链路。

AI Search 搜索、开场和对话返回的图片 ID 必须回到 Piancton 数据库校验，只展示当前本地素材库能够读取的图片。外部推荐不能创建图片、改变卖点关系或绕过人工确认。用户行为可以成为火山侧个性化、热度和推荐学习信号，但本地不把下载量硬编码为压过卖点相关性的首要排序条件。

图片详情页把入口分成两层：卖点关系形成“相似素材”，优先展示与当前图片支撑同一卖点的其它表达；PPT、官网、手机端大图、手机端小图、品牌手册和当前渠道则是各自独立的个性化推荐入口。火山 AI Search 详情页推荐场景携带当前业务账号 `user_id` 和父图片 `_id` 返回候选，Piancton 回查本地已发布图片和人工渠道事实后，将候选分别排进对应渠道入口，而不是额外显示一个笼统的“为你推荐”栏。没有足够行为或上游失败时，各渠道入口仍按本地渠道事实提供素材。同组其它尺寸仍在素材版本区选择，不属于相似推荐。

在当前应用的“推荐体验”中另建一个详情页推荐场景，继续关联现有物品数据集和现有用户行为数据集；发布后把控制台给出的场景 API 路径写入服务器 `.env`：

```dotenv
AI_SEARCH_RECOMMEND_ENABLED=true
AI_SEARCH_RECOMMEND_PATH=/api/v1/application/<application_id>/scene-xxxxxxxx
AI_SEARCH_RECOMMEND_TIMEOUT_SECONDS=8
```

这一步只增加推荐场景，不创建或更换数据集。路径未配置、接口超时或返回孤儿图片 ID 时，详情页继续正常显示本地三类推荐，只隐藏“为你推荐”。

## 火山控制台一次性配置

在当前 AI Search 应用中创建并绑定一个“用户行为数据集”。字段必须按以下名称和类型建立：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_id` | String | 是 | Piancton 行为事件 ID；字段名以字母开头，符合火山控制台建表规则 |
| `user_id` | String | 是 | 业务端账号的用户身份码 |
| `item_id` | String | 是 | 图片 ID，和物品数据集 `_id` 一致 |
| `event_type` | String | 是 | `exposure`、`click`、`download`、`share`、`favorite`、`unfavorite` |
| `event_timestamp` | Int64 | 是 | 毫秒时间戳 |
| `event_scene` | String | 是 | `search_results`、`agent_chat`，或详情页卖点、画面、个性化及各渠道 `detail_*` 场景 |
| `source_action` | String | 否 | Piancton 原始动作 |
| `search_log_id` | String | 否 | 首页搜索记录 ID |
| `conversation_id` | String | 否 | Agent 会话 ID |
| `position` | Int64 | 否 | 图片出现的位置 |

一个 AI Search 应用只绑定一个用户行为数据集。创建后，在服务器 `.env` 增加：

```dotenv
AI_SEARCH_BEHAVIOR_ENABLED=true
AI_SEARCH_BEHAVIOR_API_KEY=<控制台生成的实时写入 Key>
AI_SEARCH_BEHAVIOR_DATASET_ID=<控制台中的用户行为数据集 ID>
AI_SEARCH_BEHAVIOR_SYNC_INTERVAL_SECONDS=30
AI_SEARCH_BEHAVIOR_SYNC_BATCH_SIZE=100
AI_SEARCH_BEHAVIOR_SYNC_STARTUP_DELAY_SECONDS=10
```

实时写入 Key 与搜索/问答使用的 `AI_SEARCH_API_KEY` 分开保存，避免轮换其中一个 Key 时影响另一条链路。为了兼容已经部署的旧环境，未设置 `AI_SEARCH_BEHAVIOR_API_KEY` 时会暂时回退使用 `AI_SEARCH_API_KEY`，新部署应显式填写独立的实时写入 Key。

`datasets/ai_search_behavior/sample.jsonl` 只用于查看字段格式；其中 `sample-user`、`sample-item` 是占位值，不得上传。首次创建数据集时可在本地临时生成 `datasets/ai_search_behavior/bootstrap.jsonl`，其中只放一条用于建立 Schema 的曝光记录：`user_id` 使用业务测试账号的用户身份码，`item_id` 使用已经在线上物品数据集中的图片 ID；该临时文件已被 Git 忽略，不得提交。行为事件唯一标识使用 `event_id`，不得使用会被火山建表校验拒绝的 `_id`；物品数据集本身的图片 `_id` 不受影响。这条技术初始化曝光不代表真实业务偏好；数据集创建后，后续只由 Piancton 实时写入真实业务账号的行为。真实事件中的 `item_id` 必须与物品数据集中的图片 `_id` 一致。

重新构建并启动后，后台 worker 会自动同步。也可以人工检查或立即补发：

```bash
docker compose exec -T backend python -m scripts.sync_ai_search_behavior_events --dry-run
docker compose exec -T backend python -m scripts.sync_ai_search_behavior_events
```

## 数据边界

行为数据用于 AI Search 的个性化检索、物品热度和推荐训练。只有 `role=business` 的账号有资格进入外部行为数据集；管理员和设计师仅进入本地运营统计。行为数据不能修改本地图片、六大体系、核心卖点、证明点或人工审核关系；Piancton 数据库始终是业务事实源。
