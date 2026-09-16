from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.channel_folder import ChannelFolder, ImageChannelPlacement, ManagedChannel
from app.models.image import Image


class ChannelFolderRepository:
    def __init__(self, db: Session):
        self.db = db

    def channels(self) -> list[ManagedChannel]:
        return list(self.db.scalars(select(ManagedChannel).order_by(ManagedChannel.name)).all())

    def channel(self, name: str) -> ManagedChannel | None:
        return self.db.get(ManagedChannel, name)

    def add_channel(self, channel: ManagedChannel) -> None:
        self.db.add(channel)

    def folders(self, channel: str) -> list[ChannelFolder]:
        return list(
            self.db.scalars(
                select(ChannelFolder)
                .where(ChannelFolder.channel_name == channel)
                .order_by(ChannelFolder.name)
            ).all()
        )

    def folder(self, folder_id: str) -> ChannelFolder | None:
        return self.db.get(ChannelFolder, folder_id)

    def add_folder(self, folder: ChannelFolder) -> None:
        self.db.add(folder)

    def remove_folder(self, folder_id: str) -> None:
        self.db.execute(delete(ChannelFolder).where(ChannelFolder.id == folder_id))

    def images(self, image_ids: list[str]) -> list[Image]:
        return list(
            self.db.scalars(
                select(Image).where(Image.id.in_(image_ids), Image.deleted_at.is_(None))
            ).all()
        )

    def placements(self, image_ids: list[str], channel: str) -> list[ImageChannelPlacement]:
        return list(
            self.db.scalars(
                select(ImageChannelPlacement).where(
                    ImageChannelPlacement.image_id.in_(image_ids),
                    ImageChannelPlacement.channel_name == channel,
                )
            ).all()
        )

    def image_placements(self, image_id: str) -> list[ImageChannelPlacement]:
        return list(
            self.db.scalars(
                select(ImageChannelPlacement).where(ImageChannelPlacement.image_id == image_id)
            ).all()
        )

    def remove_placement(self, placement: ImageChannelPlacement) -> None:
        self.db.delete(placement)

    def add_placement(self, placement: ImageChannelPlacement) -> None:
        self.db.add(placement)

    def remove_placements(self, image_ids: list[str], channel: str) -> None:
        self.db.execute(
            delete(ImageChannelPlacement).where(
                ImageChannelPlacement.image_id.in_(image_ids),
                ImageChannelPlacement.channel_name == channel,
            )
        )

    def placement_count_for_folders(self, folder_ids: list[str]) -> int:
        if not folder_ids:
            return 0
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(ImageChannelPlacement)
                .where(ImageChannelPlacement.folder_id.in_(folder_ids))
            )
            or 0
        )

    def remove_placements_for_folders(self, folder_ids: list[str]) -> None:
        if not folder_ids:
            return
        self.db.execute(
            delete(ImageChannelPlacement).where(ImageChannelPlacement.folder_id.in_(folder_ids))
        )
