"""Seed a shared read-only Demo Collection with sample documents."""

from __future__ import annotations

import io
import json
import logging
import uuid
from pathlib import Path

from flask import current_app
from sqlalchemy import inspect, text
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models.document import Chunk, Collection, Document
from app.models.user import Status, User
from app.services.bm25_index import BM25Index, tokenize
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

DEMO_SYSTEM_USER_ID = "00000000-0000-4000-8000-000000000001"
DEMO_SYSTEM_EMAIL = "demo@system.local"
DEMO_COLLECTION_NAME = "Demo Collection"
DEMO_DOCS_DIR = Path(__file__).resolve().parent.parent / "demo_docs"


def _ensure_is_demo_column() -> None:
    """Add collections.is_demo on existing databases that predate the column."""
    try:
        inspector = inspect(db.engine)
        if "collections" not in inspector.get_table_names():
            return
        columns = {col["name"] for col in inspector.get_columns("collections")}
        if "is_demo" in columns:
            return
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE collections ADD COLUMN is_demo BOOLEAN "
                    "DEFAULT FALSE NOT NULL"
                )
            )
        logger.info("Added collections.is_demo column")
    except Exception as exc:
        logger.warning("Could not ensure is_demo column: %s", exc)


def _ensure_demo_user() -> User:
    user = db.session.get(User, DEMO_SYSTEM_USER_ID)
    if user:
        return user
    user = User(
        id=DEMO_SYSTEM_USER_ID,
        email=DEMO_SYSTEM_EMAIL,
        # Non-login system account; hash for "password" (unused)
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        status=Status.ACTIVE,
        guest_user_session_id=None,
    )
    db.session.add(user)
    db.session.commit()
    logger.info("Created demo system user")
    return user


def _ingest_demo_file(collection_id: int, path: Path) -> None:
    """Parse, chunk, embed, and index one demo .txt file (no S3)."""
    existing = Document.query.filter_by(
        collection_id=collection_id, filename=path.name
    ).first()
    if existing and existing.status == "ready":
        return

    raw = path.read_bytes()
    file = FileStorage(
        stream=io.BytesIO(raw),
        filename=path.name,
        content_type="text/plain",
    )
    try:
        if existing:
            document = existing
            document.status = "processing"
            document.error_message = None
            Chunk.query.filter_by(document_id=document.id).delete()
        else:
            document = Document(
                collection_id=collection_id,
                filename=path.name,
                file_path=str(path),
                file_size=len(raw),
                status="processing",
            )
            db.session.add(document)
        db.session.commit()

        processor = current_app.extensions["document_processor"]
        result = processor.process_document(file, path.name)

        chunk_ids = []
        for chunk_data in result["chunks"]:
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            db.session.add(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    collection_id=collection_id,
                    content=chunk_data["content"],
                    page_number=chunk_data["page_number"],
                    chunk_index=chunk_data["chunk_index"],
                    metadata_json=json.dumps(chunk_data["metadata"]),
                    chunk_tokens=tokenize(chunk_data["content"]),
                )
            )
        db.session.commit()

        embedding_service = current_app.extensions["embedding_service"]
        texts = [c["content"] for c in result["chunks"]]
        embeddings = embedding_service.embed_texts(texts)
        vector_metadata = [
            {
                "document_id": document.id,
                "chunk_index": c["chunk_index"],
                "page_number": c["page_number"],
                "source": path.name,
                "content": c["content"],
            }
            for c in result["chunks"]
        ]
        VectorStore().add_vectors(
            collection_id=collection_id,
            chunk_ids=chunk_ids,
            embeddings=embeddings,
            metadata_list=vector_metadata,
        )
        BM25Index().add_documents(collection_id=collection_id)

        document.page_count = result["page_count"]
        document.chunk_count = result["chunk_count"]
        document.status = "ready"
        db.session.commit()
        logger.info("Ingested demo document %s (%s chunks)", path.name, result["chunk_count"])
    except Exception as exc:
        logger.error("Failed to ingest demo doc %s: %s", path.name, exc)
        db.session.rollback()
        doc = Document.query.filter_by(
            collection_id=collection_id, filename=path.name
        ).first()
        if doc:
            doc.status = "error"
            doc.error_message = str(exc)
            db.session.commit()


def seed_demo_collection() -> Collection | None:
    """
    Ensure a shared Demo Collection exists and is indexed.

    Safe to call on every app startup; skips work when already ready.
    """
    _ensure_is_demo_column()
    _ensure_demo_user()

    collection = Collection.query.filter_by(is_demo=True).first()
    if not collection:
        collection = Collection(
            name=DEMO_COLLECTION_NAME,
            description=(
                "Sample documents so you can try the assistant immediately. "
                "Create your own collection to upload PDFs."
            ),
            user_id=DEMO_SYSTEM_USER_ID,
            is_demo=True,
        )
        db.session.add(collection)
        db.session.commit()
        logger.info("Created Demo Collection id=%s", collection.id)

    ready_docs = Document.query.filter_by(
        collection_id=collection.id, status="ready"
    ).count()
    if ready_docs > 0:
        logger.info("Demo Collection already seeded (%s ready docs)", ready_docs)
        return collection

    if not DEMO_DOCS_DIR.is_dir():
        logger.warning("Demo docs directory missing: %s", DEMO_DOCS_DIR)
        return collection

    for path in sorted(DEMO_DOCS_DIR.glob("*.txt")):
        _ingest_demo_file(collection.id, path)

    return collection
