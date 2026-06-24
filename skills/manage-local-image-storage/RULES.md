# 本地图片存储 Skill

用途：管理图片字节、路径安全，并为以后替换 OSS/S3 保留边界。

## 存储协议

Current root: `storage/images`.

Required operations:

- `save_upload(upload) -> stored_name, absolute_path`
- `delete(file_path) -> None`
- resolve a stored path for download

Safety rules:

- UUID-based stored names.
- Preserve only a normalized extension.
- Never concatenate client path fragments.
- Delete only descendants of the configured root.
- Database rows store metadata; image bytes stay out of SQLite.
