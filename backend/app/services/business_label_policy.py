from __future__ import annotations

from app.models.image import ImageBusinessLabel


class BusinessLabelPolicy:
    """Centralizes business-label trust and ranking rules."""

    def label_weight(self, label: ImageBusinessLabel) -> float:
        if label.origin == "manual":
            return 1.0 if label.role == "primary" else 0.95
        if label.origin == "ai" and label.review_status == "accepted":
            return 0.9
        if label.origin == "ai" and label.review_status == "pending":
            return 0.62
        return 0.0

    def is_searchable(self, label: ImageBusinessLabel) -> bool:
        return label.review_status != "rejected" and self.label_weight(label) > 0

    def is_trusted(self, label: ImageBusinessLabel) -> bool:
        return label.origin == "manual" or (
            label.origin == "ai" and label.review_status == "accepted"
        )

    def is_pending_ai(self, label: ImageBusinessLabel) -> bool:
        return label.origin == "ai" and label.review_status == "pending"

    def display_name(self, label: ImageBusinessLabel) -> str:
        if label.tag.parent:
            return f"{label.tag.parent.name} > {label.tag.name}"
        return label.tag.name
