"""Chat and query API endpoints with SSE streaming."""

import json
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.config import Config
from app.extensions import db
from app.models.document import Collection
from app.models.chat import Conversation, Message
from app.services.rag_pipeline import RAGPipeline
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
import re

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/conversations/collection/<int:collection_id>", methods=["GET"])
def list_conversations(collection_id):
    """List all conversations in a collection."""
    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    chat_service = ChatService()
    conversations = chat_service.get_conversations_for_collection(collection_id)
    return jsonify([c.to_dict() for c in conversations])


@chat_bp.route("/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation."""
    data = request.get_json()
    if not data or not data.get("collection_id"):
        return jsonify({"error": "collection_id is required"}), 400

    collection = db.session.get(Collection, data["collection_id"])
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    chat_service = ChatService()
    conversation = chat_service.create_conversation(
        collection_id=data["collection_id"],
        title=data.get("title", "New Conversation"),
    )
    return jsonify(conversation.to_dict()), 201


@chat_bp.route("/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get a conversation with its messages, supporting pagination."""
    limit = request.args.get("limit", 10, type=int)
    before_id = request.args.get("before_id", type=int)
    limit = min(limit, 100)

    chat_service = ChatService()
    conversation = chat_service.get_conversation(conversation_id)

    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    messages = chat_service.get_conversation_messages(conversation_id, limit+1, before_id)
    messages.reverse()

    conv_dict = conversation.to_dict(include_messages=False)
    
    if(len(messages)>limit):
        messages = messages[1:]
        conv_dict["messages"] = [m.to_dict() for m in messages]
        conv_dict["hasOlder"] = True
    else: 
        conv_dict["messages"] = [m.to_dict() for m in messages]
        conv_dict["hasOlder"] = False
    return jsonify(conv_dict)





@chat_bp.route("/conversations/<int:conversation_id>", methods=["PATCH"])
def update_conversation(conversation_id):
    """Update a conversation."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    chat_service = ChatService()
    conversation = chat_service.update_conversation(conversation_id, data)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify(conversation.to_dict())

@chat_bp.route("/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """Delete a conversation."""
    chat_service = ChatService()
    if chat_service.delete_conversation(conversation_id):
        return jsonify({"message": "Conversation deleted"})
    return jsonify({"error": "Conversation not found"}), 404


@chat_bp.route("/query", methods=["POST"])
def query():
    """
    Send a query to the RAG pipeline (non-streaming).

    Request body:
    {
        "question": "string",
        "collection_id": int,
        "conversation_id": int (optional),
        "provider": "string" (optional),
        "model_name": "string" (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    question = data.get("question", "").strip()
    question = re.sub(r"\s+", " ", question)

    if(len(question) > Config.MAX_QUESTION_LENGTH):
        return jsonify({"error": "Question too long (Max length: 500 chars)"})
    collection_id = data.get("collection_id")

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if not collection_id:
        return jsonify({"error": "collection_id is required"}), 400

    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    conversation_id = data.get("conversation_id")
    provider = data.get("provider")
    model_name = data.get("model_name")

    #Validate conversation_id belongs to collection_id
    chat_service = ChatService()
    if conversation_id:
        conversation = chat_service.get_conversation(conversation_id)
        if(collection_id != conversation.collection_id):
            return jsonify({"error": "Conversation does not belong to collection"})


    # Create conversation if not provided
    if not conversation_id:
        conversation = chat_service.create_conversation(collection_id)
        conversation_id = conversation.id

    # Save user message
    chat_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=question,
    )

    # Run RAG pipeline
    rag = RAGPipeline()
    result = rag.query(
        collection_id=collection_id,
        question=question,
        conversation_id=conversation_id,
        provider=provider,
        model_name=model_name,
    )

    # Save assistant message
    message = chat_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
        model_name=result["model_info"]["model"],
        provider=result["model_info"]["provider"],
    )

    return jsonify({
        "answer": result["answer"],
        "citations": result["citations"],
        "conversation_id": conversation_id,
        "message_id": message.id,
        "model_info": result["model_info"],
    })


@chat_bp.route("/query/stream", methods=["POST"])
def query_stream():
    """
    Send a query to the RAG pipeline with SSE streaming.

    Returns Server-Sent Events with:
    - event: chunks (retrieved context)
    - event: token (individual generated tokens)
    - event: done (final answer with citations)
    - event: error (error messages)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    question = data.get("question", "").strip()
    collection_id = data.get("collection_id")

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if not collection_id:
        return jsonify({"error": "collection_id is required"}), 400

    collection = db.session.get(Collection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    conversation_id = data.get("conversation_id")
    provider = data.get("provider")
    model_name = data.get("model_name")

    
    #Validate conversation_id belongs to collection_id
    chat_service = ChatService()
    if conversation_id:
        conversation = chat_service.get_conversation(conversation_id)
        if(collection_id != conversation.collection_id):
            return jsonify({"error": "Conversation does not belong to collection"})

    # Create conversation if needed
    if not conversation_id:
        conversation = chat_service.create_conversation(collection_id)
        conversation_id = conversation.id

    # Save user message
    chat_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=question,
    )

    def generate():
        rag = RAGPipeline()
        final_data = None

        for event in rag.query_stream(
            collection_id=collection_id,
            question=question,
            conversation_id=conversation_id,
            provider=provider,
            model_name=model_name,
        ):
            event_type = event["type"]
            event_data = json.dumps(event["data"])

            if event_type == "done":
                final_data = event["data"]

                # Save assistant message
                message = chat_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_data["answer"],
                    citations=final_data.get("citations", []),
                    model_name=final_data.get("model_info", {}).get("model"),
                    provider=final_data.get("model_info", {}).get("provider"),
                )

                # Include conversation_id in done event
                final_data["conversation_id"] = conversation_id
                final_data["message_id"] = message.id
                event_data = json.dumps(final_data)

            yield f"event: {event_type}\ndata: {event_data}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@chat_bp.route("/models", methods=["GET"])
def list_models():
    """List available LLM models grouped by provider."""
    return jsonify(LLMService.get_available_models())
