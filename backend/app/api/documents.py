"""Document upload and management API endpoints."""

import os
import logging
import uuid
import hashlib
from botocore.exceptions import ClientError
import io
import nltk 

from flask import Blueprint, request, jsonify, current_app,g
from werkzeug.utils import secure_filename
from datetime import datetime,timezone
from werkzeug.datastructures import FileStorage

from flask import current_app
from app.extensions import db
from app.models.document import Document, Chunk, Collection
from app.services.vector_store import VectorStore
from app.services.bm25_index import BM25Index
from app.config import Config
from app.api.auth import token_required
from app.extensions import limiter
import json 
from typing import List

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__)

# Ensure NLTK punkt tokenizer is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


def tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase and split into words."""
    return nltk.word_tokenize(text.lower())

def upload_file_to_s3(file: FileStorage,bucket: str,key: str):
    try:
        current_app.extensions['s3'].upload_fileobj(
            Fileobj=file,
            Bucket=bucket,
            Key=key
        )
        logger.info("file uploaded to s3")
    except ClientError as e:
        logger.error(f"could not upload file to s3: {e}")
    

def create_presigned_put_url(
    bucket: str,
    key: str,
    content_type: str="application/pdf",
    expires_in: int = 3600,
) -> str:
    
    try:
        url = current_app.extensions['s3'].generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to create a presigned put url:{e}")

def create_presigned_get_url(
    bucket: str,
    key: str,
    content_type: str="application/pdf",
    expires_in: int = 3600,
) -> str:
    
    try:
        url = current_app.extensions['s3'].generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to create a presigned get url:{e}")

@documents_bp.route("/collection/<int:collection_id>", methods=["GET"])
@limiter.limit("60 per minute")
@token_required
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


@documents_bp.route("/upload_url/<int:collection_id>", methods=["POST"])
@limiter.limit("20 per minute")
@token_required
def get_upload_url(collection_id):

    SUPPORTED_FILE_TYPES = [".pdf"]

    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404
    

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not any(file.filename.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES):
        return jsonify({"error": f"Only {str(SUPPORTED_FILE_TYPES)} files are supported"}), 400

    file.seek(0,2)
    file_size = file.tell()
    file.seek(0)

    if file_size > Config.MAX_CONTENT_LENGTH:
        return jsonify({"error": "File too large (max 50MB)"}), 413


    # Sanitize filename and add UUID prefix to avoid collisions
    ext = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    sanitized_name = secure_filename(file.filename) or f"document{ext}"
    safe_filename = f"{uuid.uuid4().hex[:8]}_{sanitized_name}"


    upload_url = create_presigned_put_url(bucket = Config.S3_BUCKET, key=f"uploads/{g.user["email"]}/{safe_filename}")

    return jsonify({
        "presigned_upload_put_url": upload_url
    })

@documents_bp.route("/upload/<int:collection_id>", methods=["POST"])
@limiter.limit("10 per minute")
@token_required
def upload_document(collection_id):
    """Upload a document to a collection and process it."""

    SUPPORTED_FILE_TYPES = [".pdf"]
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not any(file.filename.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES):
        return jsonify({"error": f"Only {str(SUPPORTED_FILE_TYPES)} files are supported"}), 400

    file.seek(0,2)
    file_size = file.tell()
    file.seek(0)

    if file_size > Config.MAX_CONTENT_LENGTH:
        return jsonify({"error": "File too large (max 50MB)"}), 413
    # Save the file
    upload_dir = "uploads/"+g.user["email"]+"/"+str(collection_id)+"/"+str(datetime.now(timezone.utc).date())+"/"
    # os.makedirs(upload_dir, exist_ok=True)
    
    # Sanitize filename and add UUID prefix to avoid collisions
    ext = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    sanitized_name = secure_filename(file.filename) or f"document{ext}"
    safe_filename = f"{uuid.uuid4().hex[:8]}_{sanitized_name}"
    
    file_path = os.path.join(upload_dir, safe_filename)
    
    temp_file_obj = FileStorage(stream=io.BytesIO(file.read()), filename=file.filename, content_type=file.content_type)

    upload_file_to_s3(temp_file_obj,bucket=Config.S3_BUCKET,key=file_path)
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
        processor = current_app.extensions['document_processor']
        result = processor.process_document(file, file.filename)

        # Save chunks to database
        chunk_models = []
        chunk_ids = []
        for chunk_data in result["chunks"]:

            raw_chunk_id =f"{chunk_data["metadata"]["source"]}::{chunk_data["chunk_index"]}::{chunk_data["content"]}".encode("utf-8")
            chunk_id =  hashlib.sha256(raw_chunk_id).hexdigest()
            chunk_tokens = tokenize(chunk_data["content"])
            chunk_ids.append(chunk_id)
            chunk = Chunk(
                document_id=document.id,
                collection_id=document.collection_id,
                id = chunk_id,
                content=chunk_data["content"],
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                metadata_json=json.dumps(chunk_data["metadata"]),
                chunk_tokens=chunk_tokens
            )
            chunk_models.append(chunk)
            db.session.add(chunk)

        # Generate embeddings
        embedding_service = current_app.extensions['embedding_service']
        texts = [c["content"] for c in result["chunks"]]
        embeddings = embedding_service.embed_texts(texts)

        vector_metadata = [
            {
                "document_id": document.id,
                "chunk_index": c["chunk_index"],
                "page_number": c["page_number"],
                "source": file.filename,
                "content": c["content"],
            }
            for c in result["chunks"]
        ]
        vector_store = VectorStore()
        vector_store.add_vectors(
            collection_id=collection_id,
            chunk_ids= chunk_ids,
            embeddings=embeddings,
            metadata_list = vector_metadata
        )



        # Add to BM25 index
        bm25_index = BM25Index()
        bm25_index.add_documents(
            collection_id=collection_id
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
@limiter.limit("60 per minute")
@token_required
def get_document(document_id):
    """Get a specific document."""
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(document.to_dict())


@documents_bp.route("/<int:document_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@token_required
def delete_document(document_id):
    """Delete a document and its chunks, embeddings."""
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    collection_id = document.collection_id

    # Remove from vector store
    try:
        vector_store = VectorStore()
        embedding_service = current_app.extensions['embedding_service']
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
