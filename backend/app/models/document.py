"""Document, Chunk, and Collection SQLAlchemy models."""

from datetime import datetime, timezone
from app.extensions import db


class Collection(db.Model):
    """A collection (workspace) of related documents."""

    __tablename__ = "collections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )


    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    documents = db.relationship(
        "Document", backref="collection", lazy=True, cascade="all, delete-orphan"
    )
    conversations = db.relationship(
        "Conversation", backref="collection", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "document_count": len(self.documents),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Document(db.Model):
    """An uploaded document (PDF)."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer, db.ForeignKey("collections.id"), nullable=False
    )
    filename = db.Column(db.String(512), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    page_count = db.Column(db.Integer, default=0)
    chunk_count = db.Column(db.Integer, default=0)
    status = db.Column(
        db.String(50), default="processing"
    )  # processing, ready, error
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )


    # Relationships
    chunks = db.relationship(
        "Chunk", backref="document", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


class Chunk(db.Model):
    """A text chunk extracted from a document."""

    __tablename__ = "chunks"

    id = db.Column(db.String(64), primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id"), nullable=False
    )
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    metadata_json = db.Column(db.Text, default="{}")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "metadata_json": self.metadata_json,
        }

