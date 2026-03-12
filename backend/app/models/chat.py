"""Conversation and Message SQLAlchemy models."""

import json
from datetime import datetime, timezone
from app.extensions import db


class Conversation(db.Model):
    """A chat conversation within a collection."""

    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer, db.ForeignKey("collections.id"), nullable=False
    )
    user_id = db.Column(
        db.String(40), db.ForeignKey("users.id"), nullable=False
    )
    title = db.Column(db.String(255), default="New Conversation")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    messages = db.relationship(
        "Message",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Message.created_at)",
    )

    def to_dict(self, include_messages=False):
        data = {
            "id": self.id,
            "collection_id": self.collection_id,
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class Message(db.Model):
    """A single message in a conversation."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=False
    )
    role = db.Column(db.String(20), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    citations_json = db.Column(db.Text, default="[]")
    evaluation_json = db.Column(db.Text, default="{}")
    model_name = db.Column(db.String(100), nullable=True)
    provider = db.Column(db.String(50), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    @property
    def citations(self):
        try:
            return json.loads(self.citations_json) if self.citations_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @citations.setter
    def citations(self, value):
        self.citations_json = json.dumps(value) if value else "[]"

    @property
    def evaluation(self):
        try:
            return json.loads(self.evaluation_json) if self.evaluation_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @evaluation.setter
    def evaluation(self, value):
        self.evaluation_json = json.dumps(value) if value else "{}"

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "citations": self.citations,
            "evaluation": self.evaluation,
            "model_name": self.model_name,
            "provider": self.provider,
            "created_at": self.created_at.isoformat(),
        }

