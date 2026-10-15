# Piancton 外部图片搜索 API

## 接入方式

其他项目的后端使用管理员创建的 API Key 调用 Piancton。API Key 通过请求头传递：

```http
Authorization: Bearer pk_live_xxx
```

匿名请求不会进入搜索链路。管理员在 Piancton 的“开放 API”页面创建密钥；完整密钥只在创建成功时返回一次，数据库只保存哈希。发现密钥泄露时，在同一页面撤销即可。

FastAPI 的在线开发文档部署后位于 `/docs`，接口描述也会出现在 `/openapi.json`。

## 图片搜索

```http
POST /api/public/image-search
Content-Type: application/json
Authorization: Bearer pk_live_xxx
```

请求体：

```json
{
  "query": "官网首屏使用，体现孩子遇到不会的题后通过拍照获得引导，并逐步理解解题方法的教育场景图",
  "limit": 8,
  "channel": "官网大图",
  "scene": "scene"
}
```

`query` 是必填的自然语言需求。外部 AI 不需要填写六大体系或卖点 code，Piancton 会继续完成意图识别、人工确认关系过滤和搜索排序。`limit` 默认 12，最大 50；`channel` 和 `scene` 是搜索结果后的可选收窄条件，`scene` 可取 `all`、`scene`、`nonScene`。

推荐的 query 结构是：

```text
业务目标 + 画面主体/动作 + 使用场景 + 排除条件（如果有）
```

例如“找一张教育图片”信息不足；“找一张适合官网横幅、体现孩子拍照后获得分步骤引导并理解解题思路的教育场景图，避免老师授课画面”可以直接使用。

响应沿用现有搜索响应结构。每张结果包含图片 ID、标题、匹配原因、业务概念和三类图片地址。图片地址位于 `/api/public/images/{image_id}/thumbnail`、`content` 和 `download`，访问这些地址时仍需携带同一个 Bearer Key。其他项目的后端可以代理图片给自己的前端；浏览器 `<img>` 标签不能安全地直接保存 API Key。

## 示例

```bash
curl -X POST "https://piancton.example.com/api/public/image-search" \
  -H "Authorization: Bearer pk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "适合 PPT 首页，体现个性化学习规划的教育场景图",
    "limit": 6
  }'
```

默认每个 Key 每分钟允许 60 次请求。管理员创建 Key 时可以设置自己的上限；当前限流是单进程内保护，多进程部署前需要接入共享限流存储或在网关层配置限流。

## OpenAI 兼容接口

如果接入方已经使用 OpenAI SDK，可以直接把 `base_url` 指向 Piancton 的 `/v1`，把管理员创建的 Piancton API Key 作为 `api_key`。这个接口只是图片搜索的传输适配层，不会调用外部大模型。

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://piancton.example.com/v1",
    api_key="pk_live_xxx",
)

completion = client.chat.completions.create(
    model="piancton-image-search",
    messages=[
        {
            "role": "user",
            "content": "找一张适合官网横幅、体现孩子通过拍照获得分步骤学习引导的教育场景图",
        }
    ],
    stream=False,
)
```

对应的 HTTP 地址是 `POST /v1/chat/completions`。请求必须包含一个非空的 `user` 消息；可选字段 `image_limit` 默认是 8，最大 50。第一版要求 `stream=false`。

返回值遵循 OpenAI 的 `chat.completion` 外层结构。候选图片放在 `choices[0].message.content` 的 JSON 字符串中，内容形如：

```json
{
  "query": "找一张适合官网横幅的教育场景图",
  "match_summary": "找到 3 张匹配图片",
  "images": [
    {
      "id": "image-id",
      "title": "孩子拍照学习",
      "thumbnail_url": "https://piancton.example.com/api/public/images/image-id/thumbnail",
      "content_url": "https://piancton.example.com/api/public/images/image-id/content",
      "download_url": "https://piancton.example.com/api/public/images/image-id/download",
      "match_level": "A",
      "final_score": 0.91,
      "match_reasons": ["符合教育场景", "适合官网横幅"],
      "matched_business_concepts": ["个性化学习"]
    }
  ]
}
```

外部 AI 可以读取这些候选、选择一张，再由自己的业务逻辑下载或展示。返回的三个图片地址仍然需要在请求头携带同一个 `Authorization: Bearer pk_live_xxx`；后端接入方可以代为下载并提供给自己的前端。
