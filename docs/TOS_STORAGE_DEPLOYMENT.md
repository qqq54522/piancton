# 公司 TOS 图片存储接入

对应总纲 `IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` D278。公司桶为 `ued-zhiku`，上海 `cn-shanghai`，HTTPS Endpoint 为 `https://tos-cn-shanghai.volces.com`，项目使用 `piancton/` 前缀。

## 上线前

- 控制台桶列表此前显示“公共读”。若公司素材只允许登录查看，在权限管理中将桶改为私有，并检查桶策略不存在匿名读取授权。对象默认私有不能代替桶权限检查。
- AK/SK 由公司管理员提供，授权该前缀的 PutObject、GetObject、DeleteObject；本实现不需要列出桶，也不访问其他前缀。SDK 使用 HTTPS 和 CRC 校验，上传显式设置私有 ACL。若公司策略限制设置对象 ACL，需管理员核对对应授权。
- 新图写入 TOS；原图位于 `piancton/originals/`，缩略图位于 `piancton/thumbnails/`。数据库保存 `tos-` 开头的受控 key，旧 UUID key 仍从 `image_data` 读取。不需要数据库 schema 迁移。
- 网站预览、附件下载和 ZIP 导出继续由后端鉴权后读取 TOS，文件不公开直链；无需配置浏览器跨域或 CDN。此版本仍消耗服务器转发带宽。单次读取会暂存到 `.tos-downloads`，完成、发送失败或断开连接后清理。进程被强制终止可能残留临时文件，维护时可检查该目录；不要删除整个数据卷。

## 在服务器现有项目目录执行

先确保本次 D278 代码已同步到服务器；单独运行 Docker build 不会拉取 GitHub 代码。

```sh
python3 backend/scripts/configure_tos.py
```

按提示分别粘贴 AK、SK 并回车。输入不显示字符是正常现象。脚本只替换根目录 `.env` 的 TOS 配置，保留数据库、API、VikingDB 等现有配置，文件权限设为 600。不要把密钥放在命令行参数中，不要分享 `.env` 或 `docker compose config` 的完整输出。

先构建并使用一次性容器检查真实权限，测试只写入并删除独立 UUID 小文件：

```sh
docker compose build backend
docker compose run --rm --no-deps --entrypoint python backend -m scripts.check_tos_storage
```

只有输出 `TOS upload/read/delete check passed.` 后再更新运行服务：

```sh
docker compose up -d --no-deps backend
docker compose ps
```

本次前端无需重建。随后从网站上传一张测试图，检查预览、缩略图、下载、追加版本、素材包导出、回收站恢复和永久删除。在 TOS 文件列表中可看到项目的两个路径。未登录访问网站图片接口应返回 401；桶若仍公共读，直链权限不受网站控制。

## 已有图片迁移（可选）

旧图可以继续直接使用，不要求启用前全部迁移。迁移前备份数据库和 `image_data`，安排维护窗口暂停用户操作。包括回收站中的图片也会迁移，以便恢复。

```sh
docker compose exec -T backend python -m scripts.migrate_images_to_tos
```

上面只显示数量，无写入。确认要迁移时：

```sh
docker compose stop web
docker compose exec -T backend python -m scripts.migrate_images_to_tos --apply
docker compose start web
```

工具逐条复制原图和缩略图，读回并计算 SHA-256 一致后提交数据库位置；失败则当前条目回滚并停止，已完成条目保留，重跑跳过已迁移条目。无论迁移命令是否成功，都应执行最后一条恢复 web。原本地文件保留，本轮不自动释放其硬盘空间；确认线上验收和备份后再做单独清理，不要删除整个 `image_data`。

## 故障和回退

- 503 表示配置不完整或 TOS 读写失败，不会静默切换到本地写入。检查区域、AK/SK、授权和网络，错误信息不返回 SDK 原文。
- 使用 TOS 后不要改桶名、地域或前缀，否则已保存 key 的位置会改变。
- 尚未上传/迁移远端图片时，可把 `.env` 的 `STORAGE_BACKEND` 改回 `local` 并重建 backend 容器。已有远端图片后必须保留 TOS 模式；不能只关闭开关作为回退，需恢复对应数据库和文件备份或另行回迁。
- 软删除只更新数据库。永久删除远端失败时保留回收站记录供重试；若原图已删除但缩略图删除失败，先完成永久删除重试，不应尝试恢复该不完整记录。
- 上传失败会尝试清除本次原图和缩略图；若远端连删除也不可用，日志以 `tos_upload_cleanup_failed` 和随机 key 标记待清理对象，不包含凭据。

## 验证边界

工程测试使用模拟对象存储和隔离数据库。真实公司 AK/SK 未提供给开发环境；公司桶网络、权限、资源包抵扣范围和线上上传必须按以上步骤在服务器验证后才算完成启用。
