"""Config API endpoints"""

import logging
from flask import Blueprint, jsonify,request, g
from app.services.retriever import HybridRetriever
from app.extensions import db
from app.models.document import Collection, Chunk, Document
from app.config import Config
from app.api.auth import token_required
from app.extensions import limiter
import re

logger = logging.getLogger(__name__)

retrieval_bp = Blueprint("retrieval", __name__)


@retrieval_bp.route("/search", methods=["POST"])
@limiter.limit("60 per minute")
@token_required
def get_chunks():
    request_data = request.get_json()
    collection_id = request_data.get("collection_id")
    question = request_data.get("question")

    if not collection_id:
        return jsonify({"error": "collection id is required"}), 400
    if not question: 
        return jsonify({"error": "user query is required"}), 400
    
    # validate collection id 
    collection = db.session.get(Collection, collection_id)
    if not collection or not collection.user_id==g.user['id']:
        return jsonify({"error": "Collection not found for the current user"}), 404    
    
    question = request_data.get("question", "").strip()
    question = re.sub(r"\s+", " ", question)

    if(len(question) > Config.MAX_QUESTION_LENGTH):
        return jsonify({"error": f"user question too long (Max length: {Config.MAX_QUESTION_LENGTH} chars)"}), 400
    

    retrieval_service = HybridRetriever()
    chunks = retrieval_service.retrieve(collection_id = collection_id, query = question)
    return jsonify(chunks)

@retrieval_bp.route("/stats/<int:collection_id>", methods=["GET"])
@limiter.limit("60 per minute")
@token_required
def get_collection_stats(collection_id):
    # validate collection id 
    collection = db.session.get(Collection, collection_id)
    if not collection or not collection.user_id==g.user['id']:
        return jsonify({"error": "Collection not found for the current user"}), 404    
    
    # number of chunks in the collection 
    chunks_count = Chunk.query.filter_by(collection_id = collection_id).count()
    docs = Document.query.filter_by(collection_id = collection_id).all()
    
    return jsonify({
        "chunks_count": chunks_count,
        "documents": [doc.filename for doc in docs]
    })
