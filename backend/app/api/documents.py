"""Document upload and management API endpoints."""

import os
import logging
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.document import Document, Chunk, Collection
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.bm25_index import BM25Index
from app.config import Config

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/collection/<int:collection_id>", methods=["GET"])
def list_documents(collection_id):
    """List all documents in a collection."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    documents = (
        Document.query.filter_by(collection_id=collection_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return jsonify([d.to_dict() for d in documents])


@documents_bp.route("/upload/<int:collection_id>", methods=["POST"])
def upload_document(collection_id):
    """Upload a PDF document to a collection and process it."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    # Save the file
    upload_dir = os.path.join(Config.UPLOAD_FOLDER, str(collection_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Sanitize filename and add UUID prefix to avoid collisions
    sanitized_name = secure_filename(file.filename) or "document.pdf"
    safe_filename = f"{uuid.uuid4().hex[:8]}_{sanitized_name}"
    file_path = os.path.join(upload_dir, safe_filename)
    file.save(file_path)

    file_size = os.path.getsize(file_path)

    # Create document record
    document = Document(
        collection_id=collection_id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status="processing",
    )
    db.session.add(document)
    db.session.commit()

    # Process the document
    try:
        processor = DocumentProcessor()
        result = processor.process_pdf(file_path, file.filename)

        # Save chunks to database
        chunk_models = []
        for chunk_data in result["chunks"]:
            chunk = Chunk(
                document_id=document.id,
                content=chunk_data["content"],
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                metadata_json=str(chunk_data["metadata"]),
            )
            chunk_models.append(chunk)
            db.session.add(chunk)

        # Generate embeddings
        embedding_service = EmbeddingService()
        texts = [c["content"] for c in result["chunks"]]
        embeddings = embedding_service.embed_texts(texts)

        # Build metadata for vector store
        vector_metadata = [
            {
                "document_id": document.id,
                "chunk_id": None,  # Will be updated after commit
                "chunk_index": c["chunk_index"],
                "page_number": c["page_number"],
                "source": file.filename,
                "content": c["content"],
            }
            for c in result["chunks"]
        ]

        # Add to FAISS vector store
        vector_store = VectorStore()
        vector_store.add_vectors(
            collection_id=collection_id,
            embeddings=embeddings,
            metadata_list=vector_metadata,
            dimension=embedding_service.dimension,
        )

        # Add to BM25 index
        bm25_index = BM25Index()
        bm25_index.add_documents(
            collection_id=collection_id,
            texts=texts,
            metadata_list=vector_metadata,
        )

        # Update document record
        document.page_count = result["page_count"]
        document.chunk_count = result["chunk_count"]
        document.status = "ready"
        db.session.commit()

        logger.info(
            f"Document '{file.filename}' processed: "
            f"{result['page_count']} pages, {result['chunk_count']} chunks"
        )

        return jsonify(document.to_dict()), 201

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        document.status = "error"
        document.error_message = str(e)
        db.session.commit()
        return jsonify({"error": f"Failed to process document: {str(e)}"}), 500


@documents_bp.route("/<int:document_id>", methods=["GET"])
def get_document(document_id):
    """Get a specific document."""
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(document.to_dict())


@documents_bp.route("/<int:document_id>", methods=["DELETE"])
def delete_document(document_id):
    """Delete a document and its chunks, embeddings."""
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    collection_id = document.collection_id

    # Remove from vector store
    try:
        vector_store = VectorStore()
        embedding_service = EmbeddingService()
        vector_store.delete_document_vectors(
            collection_id=collection_id,
            document_id=document_id,
            dimension=embedding_service.dimension,
        )
    except Exception as e:
        logger.warning(f"Error cleaning up vector store: {e}")

    # Remove from BM25 index
    try:
        bm25_index = BM25Index()
        bm25_index.delete_document(collection_id, document_id)
    except Exception as e:
        logger.warning(f"Error cleaning up BM25 index: {e}")

    # Remove file from disk
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError:
            pass

    # Delete from database (cascades to chunks)
    db.session.delete(document)
    db.session.commit()

    return jsonify({"message": "Document deleted successfully"})
