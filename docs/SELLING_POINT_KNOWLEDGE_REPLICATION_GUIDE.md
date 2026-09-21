# 卖点智库详细复刻指南

版本：2026-09-20

> 本文只写复刻操作。
>
> 不介绍项目价值、不介绍画板、不介绍排期、不解释历史技术演变，也不讨论为什么曾经使用过向量数据库、知识库或其他方案。历史研发过程统一放在：
>
> docs/SELLING_POINT_KNOWLEDGE_RESEARCH_LOG.md
>
> 复刻时只按本文执行。

## 1. 复刻目标

复刻完成后，需要得到一个可以正常使用的卖点智库环境，至少包括：

1. 项目代码可以启动。
2. 数据库迁移成功。
3. 管理员可以登录。
4. 六大体系和业务卖点已经初始化。
5. 图片可以上传、预览和下载。
6. 图片可以建立业务关系。
7. 业务用户可以搜索图片。
8. 图片身份码可以精确查找图片。
9. 管理员、设计师和业务用户权限有效。
10. 如果配置在线服务，搜索和素材 Agent 可以正常使用。
11. 如果配置现有素材数据，数据库、图片文件和业务关系保持对应。
12. 复刻结果经过健康检查、功能验收和测试检查。

只打开一个网页，不能算复刻完成。必须完成从代码、数据库、账号、图片、业务关系到搜索的完整链路。

## 2. 先选择复刻类型

开始前先决定要做哪一种。

### 2.1 空库复刻

空库复刻只恢复系统，不恢复现有素材。

包含：

- 项目代码。
- 数据库表结构。
- 六大体系。
- 业务卖点。
- 管理员账号。
- 前端和后端服务。

不包含：

- 当前已有图片。
- 现有素材关系。
- 现有用户。
- 历史会话。
- 历史搜索日志。
- 原有图片存储文件。

适合：

- 新开发机。
- 新测试环境。
- 从零初始化一套系统。
- 只想验证代码能否运行。

### 2.2 带素材数据复刻

带素材数据复刻是在空库复刻基础上，再恢复：

- 图片文件。
- 素材组。
- 图片版本。
- 当前发布状态。
- 身份码。
- 业务概念关系。
- 渠道和目录。
- 必要的素材操作数据。

适合：

- 换电脑继续工作。
- 把本地项目迁移到服务器。
- 交给其他开发者接手。
- 保留现有素材继续运营。

### 2.3 完整在线复刻

完整在线复刻是在带数据复刻基础上，再配置：

- 在线搜索应用。
- 在线聊天能力。
- 在线图片数据集。
- 在线推荐或行为能力。
- 外部可访问的图片地址。
- 真实代表图片搜索验收。

适合：

- 测试完整业务流程。
- 服务器部署。
- 业务用户正式使用。
- 验证素材 Agent 和图片问答。

## 3. 复刻前准备

### 3.1 必需软件

本地开发至少准备：

| 软件 | 用途 |
| --- | --- |
| Git | 获取和更新代码 |
| Python | 运行后端和脚本 |
| pip | 安装后端依赖 |
| Node.js | 运行前端 |
| npm | 安装前端依赖 |

服务器部署还需要：

| 软件 | 用途 |
| --- | --- |
| Docker | 运行容器 |
| Docker Compose | 启动数据库、后端和前端 |
| PostgreSQL 持久化卷 | 保存数据库 |
| 图片存储卷或对象存储 | 保存原图和缩略图 |

### 3.2 推荐版本

- Python：推荐 3.11 或 3.12。
- Node.js：推荐 22。
- Docker：使用当前服务器支持的稳定版本。
- PostgreSQL：Docker 配置默认使用项目指定版本。

不要使用过旧 Python。当前代码使用现代类型注解，过旧解释器可能在导入模型时直接失败。

### 3.3 环境自检

逐条执行：

~~~bash
git --version
python3 --version
node -v
npm -v
docker --version
docker compose version
~~~

如果只做本地开发，Docker 不是必需项；如果做服务器复刻，Docker 和 Docker Compose 都必须可用。

环境自检成功标准：

- 每条命令都能输出版本号。
- 没有 command not found。
- Python 版本符合项目要求。
- Node 和 npm 可以正常执行。
- Docker Compose 可以识别。

如果 Python 版本过低，先安装正确版本，再重新创建虚拟环境。不要在旧虚拟环境上继续安装依赖。

## 4. 获取代码

### 4.1 使用 Git 获取代码

进入准备放置项目的目录：

~~~bash
git clone 项目仓库地址 piancton
cd piancton
~~~

如果代码已经存在：

~~~bash
cd /path/to/piancton
git status
~~~

先确认当前目录确实是项目根目录。项目根目录至少应该能看到：

~~~text
backend/
client/
docs/
skills/
taxonomy/
docker-compose.yml
Makefile
.env.docker.example
~~~

### 4.2 检查是否有未提交改动

如果是从已有工作机复制出来的代码，先执行：

~~~bash
git status --short
~~~

如果存在已有改动：

- 不要直接覆盖。
- 不要执行清空工作区的命令。
- 先确认这些改动是否属于当前复刻内容。
- 数据库和图片目录也要单独确认。

复刻通常是在新目录执行；如果在已有工作目录复刻，必须先确认不会覆盖原环境数据。

## 5. 本地空库复刻

本节用于在开发电脑上从零运行一套空库环境。

### 5.1 复制后端环境变量

在项目根目录执行：

~~~bash
cp backend/.env.example backend/.env
~~~

确认文件存在：

~~~bash
ls -l backend/.env
~~~

### 5.2 配置本地数据库和图片目录

打开 backend/.env，确认本地基础配置：

~~~dotenv
DATABASE_URL=sqlite:///../data/piancton.db
STORAGE_DIR=../storage/images
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
PUBLIC_BASE_URL=http://127.0.0.1:5173
SESSION_COOKIE_SECURE=false
SEARCH_BACKEND=database
AI_SEARCH_ENABLED=false
~~~

第一次复刻时先使用 SQLite 和本地图片目录，便于确认基础链路。

需要确认：

- data 目录存在或可创建。
- storage/images 目录存在或可创建。
- backend/.env 使用的是当前项目路径。
- 没有误填另一个环境的数据库地址。
- 没有把生产 HTTPS 配置复制到本地 HTTP 环境。

### 5.3 创建后端虚拟环境

进入 backend：

~~~bash
cd backend
~~~

创建虚拟环境：

~~~bash
python3 -m venv .venv
~~~

激活虚拟环境：

~~~bash
source .venv/bin/activate
~~~

Windows 环境使用项目对应的激活方式。

确认当前 Python 来自虚拟环境：

~~~bash
which python
python --version
~~~

安装依赖：

~~~bash
pip install -r requirements-dev.txt
~~~

如果安装失败，记录：

- Python 版本。
- pip 版本。
- 失败的依赖名称。
- 网络或证书错误。
- 是否使用了错误的虚拟环境。

不要在未激活虚拟环境时把依赖安装到系统 Python。

### 5.4 执行数据库迁移

仍然在 backend 目录执行：

~~~bash
alembic upgrade head
~~~

成功标准：

- 命令正常结束。
- 没有数据库连接错误。
- 没有迁移冲突。
- 当前数据库文件已经创建或已更新。

如果失败，按顺序检查：

1. 当前目录是否为 backend。
2. backend/.env 是否存在。
3. DATABASE_URL 是否正确。
4. data 目录是否有写权限。
5. 是否激活了正确虚拟环境。
6. 是否有旧数据库文件损坏。
7. 是否使用了不兼容的 Python 版本。

不要手工创建数据库表。所有表结构必须通过 Alembic 迁移生成。

### 5.5 初始化业务体系和卖点

执行：

~~~bash
python -m scripts.seed_taxonomy
~~~

这个步骤用于初始化项目需要的业务目录和概念种子。

成功后检查：

- 六大体系存在。
- 业务卖点存在。
- 概念和体系关系存在。
- 脚本没有报错。
- 重复执行不会生成重复数据。

seed 脚本是幂等初始化脚本。正常情况下可以重复执行，但不要用它代替业务人员修改正式概念和人工关系。

### 5.6 创建管理员

执行：

~~~bash
python -m scripts.create_admin admin 'replace-with-a-strong-password'
~~~

把占位密码替换为强密码。

成功标准：

- 命令正常结束。
- 当前数据库中出现管理员账号。
- 能使用该账号登录。

如果提示用户名已存在：

- 不要随意删除数据库。
- 可以使用已有账号。
- 或确认后更换一个测试管理员用户名。
- 如果是全新空库但仍提示已存在，检查 DATABASE_URL 是否连接到了旧数据库。

### 5.7 启动后端

在 backend 目录运行：

~~~bash
uvicorn app.main:app --reload --port 8000
~~~

保持这个终端持续运行。

打开健康检查：

~~~text
http://127.0.0.1:8000/health
~~~

同时可以打开接口文档：

~~~text
http://127.0.0.1:8000/docs
~~~

后端启动成功标准：

- 终端显示服务已监听 8000。
- /health 可以访问。
- 数据库连接成功。
- 没有启动导入错误。
- 没有模型或环境变量导入异常。

### 5.8 启动前端

新开第二个终端：

~~~bash
cd /path/to/piancton/client
npm ci
npm run dev
~~~

打开终端输出的前端地址，通常是：

~~~text
http://127.0.0.1:5173
~~~

前端启动成功标准：

- 登录页可以打开。
- 浏览器控制台没有阻断性错误。
- 前端请求地址指向当前后端。
- 页面不是旧构建缓存。

### 5.9 本地空库第一次登录

使用刚刚创建的管理员账号登录。

登录后检查：

1. 首页能打开。
2. 管理员菜单存在。
3. 六大体系页面能打开。
4. 卖点或业务概念页面能打开。
5. 用户管理和审计页面权限正确。
6. 页面请求没有 401、403 或 500。

如果页面能打开但登录失败：

1. 查看后端终端日志。
2. 确认前端请求的是 8000 端口。
3. 确认 CORS_ORIGINS 包含 5173。
4. 确认管理员创建到了当前数据库。
5. 确认浏览器没有保留另一个环境的 Cookie。

## 6. 本地素材复刻

### 6.1 只恢复现有素材时必须迁移什么

至少需要同时迁移：

~~~text
数据库文件
图片原图
图片缩略图
回收站文件
必要的环境变量
~~~

默认 SQLite 环境通常对应：

~~~text
data/piancton.db
storage/images/
~~~

只复制数据库而不复制图片，页面可能有记录但打不开图片。

只复制图片而不复制数据库，系统无法知道图片属于哪个素材组、版本、用户、渠道和业务关系。

### 6.2 先备份源环境

进入源环境 backend：

~~~bash
cd backend
source .venv/bin/activate
python -m scripts.backup_local_assets
~~~

备份前确认：

- 没有正在进行的上传。
- 没有正在进行的删除或恢复。
- 数据库文件可读。
- 图片目录可读。
- 备份目录有足够空间。
- 备份文件没有被 Git 跟踪。

记录备份内容：

- 数据库文件。
- 图片数量。
- 素材组数量。
- 当前图片数量。
- 发布图片数量。
- accepted 关系数量。
- 备份时间。
- 当前代码提交或分支。

### 6.3 复制本地 SQLite 素材

目标机器先完成代码和依赖安装，再停止后端服务，复制：

~~~text
源 data/piancton.db
→ 目标 data/piancton.db

源 storage/images/
→ 目标 storage/images/
~~~

复制后执行：

~~~bash
cd backend
alembic upgrade head
python -m scripts.seed_taxonomy
~~~

再启动后端和前端。

检查：

- 素材列表数量。
- 图片预览。
- 图片详情。
- 身份码。
- 当前版本。
- 发布状态。
- 人工关系。
- 下载权限。

### 6.4 SQLite 恢复到 PostgreSQL

SQLite 文件不能直接作为 PostgreSQL 数据库文件使用。

正确顺序：

1. 启动 PostgreSQL。
2. 执行目标数据库迁移。
3. 初始化目标体系和业务概念。
4. 备份目标数据库。
5. 对源 SQLite 执行 dry-run。
6. 核对将恢复的素材和图片数量。
7. 正式执行恢复。
8. 检查目标图片目录。
9. 检查素材、版本和人工关系。
10. 再进行在线数据同步。

dry-run 示例：

~~~bash
docker compose exec backend python -m scripts.restore_assets_from_sqlite \
  --source-db /path/to/piancton.db \
  --source-images /path/to/storage/images \
  --target-images /data/images \
  --dry-run
~~~

确认数量和路径都正确后，再去掉 dry-run 参数。

恢复后不要直接删除源数据库和源图片。至少完成一次登录、图片打开、搜索和下载验证后再处理源数据。

## 7. Docker 服务器复刻

### 7.1 创建 Docker 配置

进入项目根目录：

~~~bash
cp .env.docker.example .env
~~~

编辑根目录 .env。

至少设置：

~~~dotenv
POSTGRES_DB=piancton
POSTGRES_USER=piancton
POSTGRES_PASSWORD=替换为强密码
CORS_ORIGINS=https://你的正式域名
PUBLIC_BASE_URL=https://你的正式域名
SESSION_COOKIE_SECURE=true
WEB_PORT=80
~~~

如果暂时使用 HTTP IP 测试：

~~~dotenv
CORS_ORIGINS=http://服务器IP
PUBLIC_BASE_URL=http://服务器IP
SESSION_COOKIE_SECURE=false
~~~

正式 HTTPS 上线前，必须重新设置 SESSION_COOKIE_SECURE=true。

### 7.2 先检查 Compose 配置

执行：

~~~bash
docker compose config
~~~

这一步只检查配置是否能解析，不代表服务已经启动。

重点检查：

- 环境变量是否被替换。
- 数据库密码是否存在。
- 端口是否冲突。
- 卷路径是否正确。
- AI Search 配置是否为空或来自错误环境。
- 是否意外开启了不需要的旧服务。

### 7.3 启动服务

执行：

~~~bash
docker compose up --build -d
docker compose ps
~~~

等待容器完成构建和健康检查。

查看日志：

~~~bash
docker compose logs postgres --tail=120
docker compose logs backend --tail=120
docker compose logs web --tail=120
~~~

### 7.4 Docker 初始化

执行：

~~~bash
docker compose exec backend python -m scripts.seed_taxonomy
docker compose exec backend python -m scripts.create_admin admin 'replace-with-a-strong-password'
~~~

打开：

~~~text
http://服务器IP
~~~

或：

~~~text
https://正式域名
~~~

### 7.5 Docker 成功标准

必须确认：

- postgres healthy。
- backend healthy。
- web healthy。
- /health/ready 返回 ready。
- 管理员可以登录。
- 六大体系和卖点存在。
- 上传测试图片成功。
- 重启容器后数据仍然存在。
- 图片卷没有被重新创建为空。
- 数据库卷没有被重新创建为空。

如果服务不健康，不要先反复执行 up --build。先查看日志并判断是：

| 服务 | 优先检查 |
| --- | --- |
| postgres | 密码、卷、磁盘空间、容器日志 |
| backend | 数据库连接、迁移、环境变量、启动日志 |
| web | 构建、Nginx 代理、端口、backend 健康状态 |

## 8. 在线搜索服务复刻：从火山引擎控制台开始

如果你是第一次复刻，前面本地空库和 Docker 步骤完成后，不要直接填写一堆空的环境变量。你还没有火山侧资源时，必须先在火山引擎开通并创建 Viking AI 搜索资源。

火山官方产品名称是“Viking AI 搜索”。官方入口：

- https://www.volcengine.com/docs/85296
- https://www.volcengine.com/docs/85296/1873487
- https://www.volcengine.com/docs/85296/2525012

控制台菜单名称可能随版本调整，但要找的对象不会变：账号、服务开通、API Key、数据集、应用、搜索场景、问答配置和推荐场景。

### 8.1 注册火山引擎账号并开通 Viking AI 搜索

1. 打开火山引擎官网并登录企业账号。
2. 进入控制台，在产品搜索中搜索“Viking AI 搜索”或“AI 搜索”。
3. 进入 Viking AI 搜索控制台，不要进入普通火山方舟模型页面或旧的 VikingDB 向量数据库页面。
4. 如果页面提示开通服务、选择地域或同意服务协议，按账号实际情况完成开通。
5. 记录选择的地域。项目示例使用华北北京服务地址：

~~~text
https://aisearch.cn-beijing.volces.com
~~~

如果选择其他地域，必须使用该地域对应的 AI Search 服务地址，不能只复制北京地址。

开通成功的判断：

- 能进入 Viking AI 搜索控制台。
- 能看到应用或数据集管理入口。
- 能创建或查看数据集。
- 能创建 API Key。

如果只能看到火山方舟模型服务，说明还没有进入 Viking AI 搜索产品页面。

### 8.2 创建 AI Search API Key

1. 在 Viking AI 搜索控制台找到 API Key、访问凭证或开发者配置入口。
2. 点击创建 API Key。
3. 用 piancton-test 或 piancton-production 这类名称标记用途。
4. 选择可以访问当前应用和数据集的权限。
5. 创建后立即复制完整 Key。
6. 把 Key 临时放到密码管理器。
7. 不要把 Key 发到群聊、飞书文档、Git 或截图。

这个 Key 之后填入服务端环境变量 AI_SEARCH_API_KEY，只放在服务器或本地 backend/.env，不放在 client 目录。

如果启用行为闭环，可以单独创建行为写入 Key，填入 AI_SEARCH_BEHAVIOR_API_KEY；不要把两个 Key 写反。

### 8.3 创建图片物品数据集

1. 进入数据集管理。
2. 点击创建数据集。
3. 选择物品、图片或图文搜索适用的数据集类型。
4. 命名为 piancton-images-test。
5. 选择与应用相同的地域。
6. 创建数据集。
7. 记录数据集 ID。

图片数据集至少要能保存：

| 字段 | 用途 |
| --- | --- |
| 图片唯一 ID | 回到 Piancton 的 image_id 或身份标识 |
| 图片标题 | 搜索和候选展示 |
| 图片预览地址 | 让 AI Search 读取图片 |
| 图片描述或业务文本 | 搜索理解 |
| 发布或过滤字段 | 控制同步范围 |

实际字段以控制台当前 Schema 和项目同步脚本为准。第一次只用 3-6 张代表图片，不要先上传全部图片。

### 8.4 创建业务知识数据集

如果只做普通图片搜索，可以先跳过。

如果要复刻素材 Agent：

1. 创建知识数据集。
2. 命名为 piancton-knowledge-test。
3. 导入六大体系、16 个卖点、定义、边界和业务知识。
4. 等待构建完成。
5. 记录知识数据集 ID。

将知识数据集和图片数据集一起填入：

~~~dotenv
AI_SEARCH_CHAT_DATASET_IDS=知识数据集ID,图片数据集ID
~~~

只填图片数据集不能代替知识数据集；只填知识数据集也不能保证返回本地图片卡。


### 8.5 创建应用并绑定数据集

在 Viking AI 搜索控制台进入应用管理：

1. 点击创建应用。
2. 命名为 Piancton 图片搜索测试。
3. 选择与数据集相同的地域。
4. 绑定图片物品数据集。
5. 绑定知识数据集。
6. 保存并记录应用 ID。

应用 ID 之后填入 AI_SEARCH_APPLICATION_ID。

### 8.6 创建并发布普通搜索场景

在应用内找到搜索体验、搜索策略或 Search Scene：

1. 新建搜索场景。
2. 选择图片物品数据集。
3. 配置可检索字段和图片字段。
4. 配置返回字段，确保返回图片唯一 ID。
5. 保存并发布，而不是只保存草稿。
6. 复制控制台显示的搜索场景 ID 或完整调用路径。

路径通常类似：

~~~text
/api/v1/application/应用ID/search/搜索场景ID
~~~

不要自己猜路径，也不要把推荐场景 ID 填到普通搜索路径。

控制台体验页先测试一条搜索词，确认有结果、图片 ID 和可访问预览地址。

### 8.7 配置并发布 chat_search

在同一个应用内进入问答、对话或 chat_search 配置：

1. 开启问答能力。
2. 选择知识数据集。
3. 选择图片物品数据集。
4. 配置开场白或推荐问题（如果需要）。
5. 发布问答配置。
6. 复制 chat_search 调用路径。

控制台内先测试：

- 同步校内体系是什么？
- 帮我找 AI 拍题精学图片。
- 这张图片讲了什么？

文字能回答但没有图片卡时，先检查图片数据集、图片唯一 ID 和本地图片映射，不要直接判断后端代码失败。

### 8.8 可选创建推荐场景

第一次复刻建议先跳过推荐。普通搜索、Agent 和图片卡验证成功后，再创建详情页推荐或首页猜你喜欢场景：

1. 新建推荐场景。
2. 绑定图片物品数据集。
3. 如果要个性化推荐，再绑定用户行为数据集。
4. 发布场景。
5. 复制 scene ID 或路径。

推荐配置示例：

~~~dotenv
AI_SEARCH_RECOMMEND_ENABLED=true
AI_SEARCH_RECOMMEND_PATH=/api/v1/application/应用ID/scene-详情推荐ID
AI_SEARCH_HOME_RECOMMEND_PATH=/api/v1/application/应用ID/scene-首页推荐ID
AI_SEARCH_RECOMMEND_TIMEOUT_SECONDS=8
~~~

### 8.9 可选创建用户行为数据集

如果要复刻猜你喜欢、点击、下载和收藏行为闭环，再创建行为数据集。字段至少包括 event_id、user_id、item_id、event_type、event_timestamp 和 event_scene。

创建后配置：

~~~dotenv
AI_SEARCH_BEHAVIOR_ENABLED=true
AI_SEARCH_BEHAVIOR_API_KEY=行为写入Key
AI_SEARCH_BEHAVIOR_DATASET_ID=行为数据集ID
AI_SEARCH_BEHAVIOR_SYNC_INTERVAL_SECONDS=30
AI_SEARCH_BEHAVIOR_SYNC_BATCH_SIZE=100
AI_SEARCH_BEHAVIOR_SYNC_STARTUP_DELAY_SECONDS=10
~~~

第一次复刻建议不启用行为闭环，避免把推荐问题和搜索主链路混在一起。

### 8.10 把控制台参数填写到 Piancton

在本地 backend/.env 或服务器根目录 .env 填写：

~~~dotenv
AI_SEARCH_ENABLED=true
AI_SEARCH_SYNC_ENABLED=true
AI_SEARCH_BASE_URL=https://aisearch.cn-beijing.volces.com
AI_SEARCH_API_KEY=火山AI Search API Key
AI_SEARCH_APPLICATION_ID=火山应用ID
AI_SEARCH_SEARCH_PATH=火山普通搜索场景路径
AI_SEARCH_CHAT_ENABLED=true
AI_SEARCH_CHAT_PATH=火山chat_search路径
AI_SEARCH_CHAT_DATASET_IDS=知识数据集ID,图片数据集ID
AI_SEARCH_RECOMMEND_ENABLED=false
AI_SEARCH_DATASET_ID=图片物品数据集ID
AI_SEARCH_PUBLIC_BASE_URL=https://外部可访问的图片桥地址
~~~

参数对应关系：

| 控制台内容 | 环境变量 |
| --- | --- |
| API Key | AI_SEARCH_API_KEY |
| 应用 ID | AI_SEARCH_APPLICATION_ID |
| 普通搜索场景路径 | AI_SEARCH_SEARCH_PATH |
| chat_search 路径 | AI_SEARCH_CHAT_PATH |
| 图片物品数据集 ID | AI_SEARCH_DATASET_ID |
| 知识数据集 ID | AI_SEARCH_CHAT_DATASET_IDS |
| 推荐场景路径 | AI_SEARCH_RECOMMEND_PATH |
| 行为数据集 ID | AI_SEARCH_BEHAVIOR_DATASET_ID |
| 公网图片桥地址 | AI_SEARCH_PUBLIC_BASE_URL |

不要把真实 Key 写入：

- Git。
- Markdown。
- 前端代码。
- 测试样例。
- 截图。
- 普通日志。

### 8.11 在线配置检查

逐项确认：

1. API 地址是当前应用使用的地址。
2. Application ID 没有填错环境。
3. Search path 和 Application ID 对应。
4. Chat path 和 Application ID 对应。
5. 数据集 ID 属于当前应用。
6. 图片数据集已经存在。
7. 图片预览 URL 能从外部访问。
8. 公网图片地址不是 localhost。
9. 公网图片地址不是 127.0.0.1。
10. 公网图片地址不是只对内网开放的 IP。
11. 超时配置不会超过整体搜索截止时间。
12. 服务端日志不会打印完整 Key。

### 8.12 先做普通搜索，再做视觉问图

在线验收顺序不能反过来：

1. 先检查普通搜索。
2. 再检查明确卖点搜索。
3. 再检查多卖点搜索。
4. 再检查 Agent 普通问答。
5. 再检查明确找图并返回素材卡。
6. 最后检查真实图片视觉问答。

文本搜索成功，不代表视觉问图成功。浏览器本地能打开图片，也不代表在线服务能读取图片。

## 9. 图片同步

### 9.1 同步前的本地准备

先完成：

1. 图片上传。
2. 图片预览。
3. 图片发布。
4. 人工关系确认。
5. 当前版本确认。
6. 图片地址配置。
7. 数据库备份。

### 9.2 先 dry-run

Docker 环境：

~~~bash
docker compose exec backend python -m scripts.sync_ai_search_dataset --dry-run
~~~

重点查看：

- eligible_images 数量。
- documents 数量。
- public_base_url。
- 是否包含回收站图片。
- 是否包含旧版本。
- 是否包含未发布图片。
- 是否生成了无法访问的 URL。

如果 dry-run 显示 URL 是 localhost，不要继续正式同步，先修复公网图片地址。

### 9.3 正式同步

确认 dry-run 正确后：

~~~bash
docker compose exec backend python -m scripts.sync_ai_search_dataset
~~~

同步后检查：

- 数据集中的图片数量。
- 当前发布图片数量。
- 搜索返回的 item 是否能映射本地图片。
- 删除或撤回的图片是否不再出现在正式结果。
- AI Search 同步失败是否阻断了本地上传。

同步是外部数据更新，不是本地数据库事务。外部同步失败时，仍然要保留本地图片和审核关系。

## 10. 可选搜索索引

如果部署环境需要启用 Meilisearch：

~~~bash
docker compose --profile search up -d meilisearch
docker compose exec backend python -m scripts.verify_search_index
docker compose exec backend python -m scripts.rebuild_search_index
~~~

检查：

- Meilisearch 容器健康。
- 索引可以访问。
- 重建前后数据库记录不变。
- 删除图片后索引不会继续展示。
- Meilisearch 停止后，系统仍能按允许的降级路径工作。

不要因为索引不可用就删除数据库，也不要为了替代索引恢复历史服务。

## 11. 代表图片验收

当前第一轮不需要等待全部图片准备完成。准备 3-6 张代表图即可。

每张图执行：

1. 上传。
2. 检查原图。
3. 检查缩略图。
4. 检查素材组。
5. 检查当前版本。
6. 检查身份码。
7. 发布。
8. 维护一个主要表达卖点。
9. 必要时维护支持卖点。
10. 明确不适用卖点。
11. 保存 accepted 关系。
12. 用标准卖点搜索。
13. 用口语搜索。
14. 用一个否定表达搜索。
15. 用渠道或场景筛选。
16. 检查结果卡。
17. 检查下载。
18. 把问题记录到研发日志。

负责人确认的是图片和业务卖点的关系，不是图片美观评分。

## 12. 功能验收清单

### 12.1 账号和权限

- 管理员可以登录。
- 设计师可以上传和维护素材。
- 业务用户可以搜索、预览和下载。
- 普通用户不能修改业务概念。
- 普通用户不能修改人工关系。
- 设计师不能执行管理员专属操作。
- 前端隐藏不是权限验收，必须测试后端接口权限。

### 12.2 图片和素材

- 支持的图片可以上传。
- 非图片文件会被拒绝。
- 超大文件会被拒绝。
- 原图可以预览。
- 缩略图可以加载。
- 图片身份码存在且唯一。
- 当前版本状态正确。
- 删除、恢复和回收站边界正确。
- 永久删除不会被误操作。
- 下载计数和预览行为区分。

### 12.3 业务关系

- 六大体系存在。
- 业务卖点存在。
- 图片可以关联卖点。
- accepted 关系可以保存。
- pending 关系不进入正式搜索。
- rejected 关系不进入正式搜索。
- excludes 关系不会被正向召回。
- 一张图片可以关联多个业务概念。
- 延展尺寸可以后续追加。

### 12.4 搜索

至少测试：

| 查询 | 观察点 |
| --- | --- |
| 标准卖点名 | 能否返回对应关系素材 |
| 业务口语 | 能否理解非标准表达 |
| 多卖点 | 是否保留多个独立需求 |
| 否定表达 | 是否排除被否定卖点 |
| 纯画面 | 是否不强行绑定卖点 |
| 渠道词 | 是否在结果后筛选 |
| 无素材卖点 | 是否返回空或明确提示 |
| 身份码 | 是否精确返回对应图片 |

### 12.5 Agent

- 普通业务问题可以回答。
- 明确卖点找图可以返回本地真实素材卡。
- 外部不存在的图片不能做成本地卡片。
- 图片上下文可以发送。
- 同一会话可以连续追问。
- 发送成功后不会重复堆积相同待发送图片。
- 本地图片桥不可访问时，不得假装已经看到了图片。

## 13. 常见故障排查

### 13.1 后端无法启动

依次执行：

~~~bash
python --version
which python
ls -l backend/.env
alembic current
~~~

检查：

- 是否激活正确虚拟环境。
- 是否安装 requirements-dev。
- 是否执行迁移。
- DATABASE_URL 是否正确。
- Python 是否过旧。
- 端口是否被占用。

### 13.2 测试导入时报 Python 类型错误

如果看到 unsupported operand type(s) for |：

1. 查看 Python 版本。
2. 停止当前服务。
3. 删除失败的虚拟环境。
4. 使用 Python 3.11 或更高版本重新创建。
5. 重新安装依赖。
6. 重新执行测试。

不要先修改 SQLAlchemy 模型来绕过环境问题。

### 13.3 登录失败

检查：

1. backend 是否 healthy。
2. 管理员是否创建在当前数据库。
3. 前端 API 地址是否正确。
4. CORS_ORIGINS 是否包含前端地址。
5. 是否使用了另一个数据库文件。
6. 浏览器是否保留旧 Cookie。
7. 后端是否返回 401、403 或 500。

### 13.4 图片记录存在但文件打不开

检查：

- STORAGE_DIR。
- storage/images 是否存在。
- Docker 图片卷是否挂载。
- 文件相对路径是否有效。
- 原图和缩略图是否都存在。
- TOS 的 bucket、region、prefix 是否正确。

不要先删除数据库记录。先备份，再修复存储路径或恢复图片文件。

### 13.5 搜索无结果

按以下顺序：

1. 图片是否 published。
2. 图片是否 current。
3. 素材是否有 accepted 关系。
4. 概念是否 active。
5. 查询是否带否定。
6. 渠道、场景或目录是否过窄。
7. AI Search 是否超时。
8. 上游 item 是否能水合到本地图片。
9. 是否被权限过滤。
10. 日志显示的是“无可信素材”还是系统异常。

无结果可能是正确业务结果，不要直接降低所有阈值。

### 13.6 Agent 有文字但没有图片卡

检查：

- AI Search 是否只返回名称。
- 返回的 item 是否存在本地映射。
- 本地图片是否已经发布。
- 图片是否有 accepted 关系。
- Agent Service 是否完成本地水合。
- 是否错误使用了测试占位图。

### 13.7 视觉问图失败

检查：

- AI_SEARCH_PUBLIC_BASE_URL 是否配置。
- 地址是否为 localhost 或 127.0.0.1。
- 外部服务能否访问图片。
- 图片 URL 是否过期。
- HTTPS 和权限是否正确。
- 当前图片是否已同步。
- 是否把普通文本问答成功误判为视觉问答成功。

### 13.8 Docker 服务不健康

执行：

~~~bash
docker compose ps
docker compose logs postgres --tail=120
docker compose logs backend --tail=120
docker compose logs web --tail=120
~~~

然后按服务判断：

- postgres：密码、卷、磁盘空间。
- backend：迁移、数据库连接、环境变量。
- web：构建、代理、后端健康。
- 页面：服务器端口、防火墙、安全组和域名。

不要在没有看日志的情况下反复删除卷或重建数据库。

## 14. 复刻完成后的交接

交接时至少记录：

~~~text
代码分支或提交：
Python 版本：
Node 版本：
Docker 版本：
数据库类型：
数据库迁移头：
图片存储位置：
图片备份位置：
管理员账号交接方式：
AI Search 是否配置：
图片数据集：
公网图片地址：
Meilisearch 是否启用：
代表图片数量：
已通过的验收项：
未通过的验收项：
剩余问题：
最后一次备份时间：
~~~

不要把密码和 API Key 写进交接文档。使用安全的密码交接方式。

## 15. 复刻完成标准

以下项目全部完成后，才能写“复刻完成”：

1. 代码目录完整。
2. 环境版本满足要求。
3. 后端依赖安装成功。
4. 数据库迁移成功。
5. 六大体系和业务卖点初始化成功。
6. 管理员账号可登录。
7. 前端可访问。
8. 后端健康检查通过。
9. 图片上传、预览和下载正常。
10. 图片身份码可查询。
11. 人工关系可以保存。
12. 搜索可以执行。
13. 空结果边界符合预期。
14. 权限边界符合预期。
15. 带数据复刻时数据库和图片数量核对完成。
16. 在线复刻时 AI Search 配置和同步完成。
17. Agent 普通问答和找图验收完成。
18. 视觉问图只有在公网图片桥真实验证后才能标记完成。
19. 备份和恢复路径已经记录。
20. 测试、静态检查和未完成问题已经写入项目日志。
