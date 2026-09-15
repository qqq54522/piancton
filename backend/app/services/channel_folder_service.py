from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.channel_folder import ChannelFolder, ImageChannelPlacement, ManagedChannel
from app.repositories.channel_folder_repository import ChannelFolderRepository
from app.repositories.image_repository import ImageRepository


def channel_contains(raw: str | None, channel: str) -> bool:
    values = (raw or "").replace("，", "、").replace(",", "、").replace("/", "、")
    return channel in [part.strip() for part in values.split("、")]


class ChannelFolderService:
    def __init__(self, db):
        self.db = db
        self.repo = ChannelFolderRepository(db)
        self.images = ImageRepository(db)

    def list_catalog(self) -> list[dict]:
        managed = {item.name: item for item in self.repo.channels()}
        active = set()
        for raw in self.images.list_active_channels():
            active.update(
                part.strip()
                for part in raw.replace("，", "、").replace(",", "、").split("、")
                if part.strip()
            )
        result = []
        for name in sorted(set(managed) | active):
            config = managed.get(name)
            result.append(
                {
                    "name": name,
                    "folders": [
                        {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id}
                        for folder in self.repo.folders(name)
                    ]
                    if config
                    else [],
                }
            )
        return result

    def ensure_channel(self, name: str) -> ManagedChannel:
        name = name.strip()
        if not name or len(name) > 100 or "、" in name:
            raise AppError("invalid_channel", "渠道名称无效")
        channel = self.repo.channel(name)
        if channel is None:
            channel = ManagedChannel(name=name)
            self.repo.add_channel(channel)
            self.db.flush()
        return channel

    def create_channel(self, name: str) -> None:
        if self.repo.channel(name.strip()):
            raise ConflictError("channel_exists", "渠道已存在")
        self.ensure_channel(name)
        self.db.commit()

    def create_folder(self, channel: str, name: str, parent_id: str | None) -> ChannelFolder:
        name = name.strip()
        if not name or len(name) > 80:
            raise AppError("invalid_folder", "目录名称不能为空且最多 80 字")
        self.ensure_channel(channel)
        folders = self.repo.folders(channel)
        by_id = {folder.id: folder for folder in folders}
        if parent_id and parent_id not in by_id:
            raise NotFoundError("folder_not_found", "上级目录不存在于当前渠道")
        ancestor = by_id.get(parent_id) if parent_id else None
        visited = set()
        while ancestor:
            if ancestor.id in visited:
                raise AppError("folder_cycle", "目录层级存在循环，无法创建下级")
            visited.add(ancestor.id)
            ancestor = by_id.get(ancestor.parent_id)
        if any(folder.name == name and folder.parent_id == parent_id for folder in folders):
            raise ConflictError("folder_exists", "同级目录名称已存在")
        folder = ChannelFolder(channel_name=channel, parent_id=parent_id, name=name)
        self.repo.add_folder(folder)
        self.db.commit()
        return folder

    def rename_folder(self, folder_id: str, name: str) -> None:
        folder = self.repo.folder(folder_id)
        if not folder:
            raise NotFoundError("folder_not_found", "目录不存在")
        name = name.strip()
        if not name or len(name) > 80:
            raise AppError("invalid_folder", "目录名称不能为空且最多 80 字")
        if any(
            item.id != folder.id and item.parent_id == folder.parent_id and item.name == name
            for item in self.repo.folders(folder.channel_name)
        ):
            raise ConflictError("folder_exists", "同级目录名称已存在")
        folder.name = name
        self.db.commit()

    def delete_folder(self, folder_id: str) -> None:
        folder = self.repo.folder(folder_id)
        if not folder:
            raise NotFoundError("folder_not_found", "目录不存在")
        if any(item.parent_id == folder_id for item in self.repo.folders(folder.channel_name)):
            raise ConflictError("folder_has_children", "请先整理或删除下级目录")
        if self.repo.placement_count(folder_id):
            raise ConflictError("folder_has_images", "目录仍有图片，请先批量移动图片")
        self.repo.remove_folder(folder_id)
        self.db.commit()

    def folder_ids(self, channel: str, folder_id: str) -> list[str]:
        folders = self.repo.folders(channel)
        if folder_id not in {folder.id for folder in folders}:
            raise NotFoundError("folder_not_found", "目录不存在于当前渠道")
        included = {folder_id}
        while True:
            new = {folder.id for folder in folders if folder.parent_id in included}
            if new <= included:
                break
            included |= new
        return list(included)

    def assign(self, channel: str, image_ids: list[str], folder_id: str | None) -> int:
        if not image_ids or len(image_ids) > 100:
            raise AppError("invalid_batch", "每次请选择 1 到 100 张图片")
        ids = list(dict.fromkeys(image_ids))
        rows = self.repo.images(ids)
        if len(rows) != len(ids):
            raise NotFoundError("image_not_found", "部分图片不存在或已删除")
        if any(not channel_contains(image.channel, channel) for image in rows):
            raise AppError("channel_mismatch", "所选图片不属于这个渠道")
        if folder_id:
            folder = self.repo.folder(folder_id)
            if not folder or folder.channel_name != channel:
                raise NotFoundError("folder_not_found", "目录不存在于当前渠道")
            self.ensure_channel(channel)
        existing = {item.image_id: item for item in self.repo.placements(ids, channel)}
        if folder_id is None:
            self.repo.remove_placements(ids, channel)
        else:
            for image_id in ids:
                if image_id in existing:
                    existing[image_id].folder_id = folder_id
                else:
                    self.repo.add_placement(
                        ImageChannelPlacement(
                            image_id=image_id, channel_name=channel, folder_id=folder_id
                        )
                    )
        self.db.commit()
        return len(ids)
