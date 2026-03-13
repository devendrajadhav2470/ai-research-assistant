"""Evaluation API endpoints."""

import logging
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models.chat import Message
from app.services.rag_pipeline import RAGPipeline
from app.services.chat_service import ChatService
from app.services.retriever import HybridRetriever
from app.api.auth import token_required
from app.extensions import limiter

logger = logging.getLogger(__name__)

evaluation_bp = Blueprint("evaluation", __name__)


@evaluation_bp.route("/evaluate/<int:message_id>", methods=["POST"])
@limiter.limit("20 per minute")
@token_required
def evaluate_message(message_id):
    """
    Evaluate the quality of an assistant message.

    Request body (optional):
    {
        "provider": "string",
        "model_name": "string"
    }
    """
    logger.debug("evaluate_message message_id: %s", message_id)
    message = db.session.get(Message, message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    logger.debug("evaluate_message message: %s", message)
    if message.role != "assistant":
        return jsonify({"error": "Can only evaluate assistant messages"}), 400

    # Get the user question (previous message in conversation)
    user_message = (
        Message.query.filter_by(conversation_id=message.conversation_id)
        .filter(Message.role == "user")
        .filter(Message.created_at < message.created_at)
        .order_by(Message.created_at.desc())
        .first()
    )

    if not user_message:
        return jsonify({"error": "Could not find the original question"}), 400

    # Get the collection for retrieval
    conversation = message.conversation
    collection_id = conversation.collection_id

    data = request.get_json() or {}
    provider = data.get("provider")
    model_name = data.get("model_name")

    # Re-retrieve chunks for evaluation context
    retriever = HybridRetriever()
    chunks = retriever.retrieve(
        collection_id=collection_id,
        query=user_message.content,
    )

    # Run evaluation
    rag = RAGPipeline()
    evaluation = rag.evaluate_response(
        question=user_message.content,
        answer=message.content,
        chunks=chunks,
        provider=provider,
        model_name=model_name,
    )
    logger.debug("evaluate_message evaluation: %s", evaluation)

    # Save evaluation to the message
    chat_service = ChatService()
    chat_service.update_message_evaluation(message_id, evaluation)

    return jsonify({
        "message_id": message_id,
        "evaluation": evaluation,
    })


@evaluation_bp.route("/message/<int:message_id>", methods=["GET"])
@limiter.limit("60 per minute")
@token_required
def get_evaluation(message_id):
    """Get the evaluation results for a message."""
    message = db.session.get(Message, message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    return jsonify({
        "message_id": message_id,
        "evaluation": message.evaluation,
    })
