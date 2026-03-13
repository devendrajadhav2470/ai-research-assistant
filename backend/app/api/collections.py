"""Collection CRUD API endpoints."""

from flask import Blueprint, request, jsonify,g

from app.extensions import db, limiter
from app.api.auth import token_required
import logging

from app.models.document import Collection
from app.services.vector_store import VectorStore
from app.services.bm25_index import BM25Index
logger = logging.getLogger(__name__)

collections_bp = Blueprint("collections", __name__)


@collections_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")
@token_required
def list_collections():
    """List all collections."""
    collections = Collection.query.order_by(Collection.created_at.desc()).all()
    return jsonify([c.to_dict() for c in collections])


@collections_bp.route("", methods=["POST"])
@limiter.limit("30 per minute")
@token_required
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    vector_store = VectorStore()
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    collection = Collection(
        name=data["name"],
        description=data.get("description", ""),
        user_id=g.user["id"]
    )

    db.session.add(collection)
    db.session.commit()

    return jsonify(collection.to_dict()), 201


@collections_bp.route("/<int:collection_id>", methods=["GET"])
@limiter.limit("60 per minute")
@token_required
def get_collection(collection_id):
    """Get a specific collection."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404
    return jsonify(collection.to_dict())


@collections_bp.route("/<int:collection_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@token_required
def update_collection(collection_id):
    """Update a collection."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    data = request.get_json()
    if data.get("name"):
        collection.name = data["name"]
    if "description" in data:
        collection.description = data["description"]

    db.session.commit()
    return jsonify(collection.to_dict())


@collections_bp.route("/<int:collection_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@token_required
def delete_collection(collection_id):
    """Delete a collection and all associated data."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    # Clean up vector indices
    try:
        vector_store = VectorStore()
        vector_store.delete_collection(collection_id)
        bm25_index = BM25Index()
        bm25_index.delete_collection(collection_id)
    except Exception:
        pass  # Best effort cleanup

    db.session.delete(collection)
    db.session.commit()

    return jsonify({"message": "Collection deleted successfully"})
