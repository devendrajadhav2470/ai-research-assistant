"""Helpers for collection ownership and demo access rules."""

from __future__ import annotations

from app.models.document import Collection


def can_read_collection(collection: Collection | None, user_id: str) -> bool:
    """Anyone may read/chat with the shared demo; otherwise owner only."""
    if not collection:
        return False
    if collection.is_demo:
        return True
    return collection.user_id == user_id


def can_write_collection(collection: Collection | None, user_id: str) -> bool:
    """Demo is read-only; user collections require ownership."""
    if not collection or collection.is_demo:
        return False
    return collection.user_id == user_id
