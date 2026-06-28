from __future__ import annotations

from app.models.image import Image, ImageBusinessLabel


class ImageSemanticProfileService:
    def rerank_document(self, image: Image) -> str:
        parts = [
            f"标题：{image.title}",
            f"语义总结：{image.image_summary}" if image.image_summary else "",
            "隐形标签：" + "、".join(item.tag_name for item in image.content_tags),
            "业务标签："
            + "、".join(
                self.business_label_name(label)
                for label in image.business_labels
                if label.review_status != "rejected"
            ),
            "人工标签：" + "、".join(link.tag.name for link in image.tag_links),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def business_label_name(self, label: ImageBusinessLabel) -> str:
        if label.tag.parent:
            return f"{label.tag.parent.name} > {label.tag.name}"
        return label.tag.name
