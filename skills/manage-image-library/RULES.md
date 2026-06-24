# 图片库管理 Skill

用途：图片上传、列表、详情、关联图片、编辑、下载和删除。

## 工作流

- Upload: validate upload -> save bytes -> create metadata -> attach tags.
- List: optional keyword, tags, category, cursor, limit, sort.
- Detail: image metadata + tags + content analysis + related images.
- Update title: change metadata only.
- Update tags: replace associations atomically.
- Download: resolve safe file path, increment count, stream file.
- Delete: remove database record, then delete only the owned local file.

The image entity stores title, original name, local path, uploader, download
count, categories, semantic summary, timestamps, manual tags, content tags, and
secondary categories.
