"""Chat history service for conversation management and context windowing."""

import logging
from typing import List, Dict, Optional
import datetime
from app.extensions import db
from app.models.chat import Conversation, Message
from app.config import Config
from flask import g

logger = logging.getLogger(__name__)


class ChatService:
    """Manages conversations and message history."""

    def __init__(self, history_window: int = None):
        self.history_window = history_window or Config.CHAT_HISTORY_WINDOW

    def create_conversation(
        self, collection_id: int, title: str = "New Conversation"
    ) -> Conversation:
        """Create a new conversation in a collection."""
        conversation = Conversation(
            collection_id=collection_id,
            title=title,
            user_id=g.user["id"]
        )
        db.session.add(conversation)
        db.session.commit() 
        logger.info(
            f"Created conversation {conversation.id} in collection {collection_id}"
        )
        return conversation

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return db.session.get(Conversation, conversation_id)
    
    def get_conversation_messages(self, conversation_id: int, limit: int, before_id: Optional[int] = None) -> List[Message]:
        """Get messages for a conversation."""
        query = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.id.desc())
        if before_id:
            query = query.filter(Message.id < before_id)
        messages = query.limit(limit).all()
        return messages

    def update_conversation(self, conversation_id: int, updates: dict) -> Optional[Conversation]:
        """Update a conversation."""
        conversation = db.session.get(Conversation, conversation_id)
        if conversation:
            conversation.title = updates.get("title", conversation.title)
            conversation.updated_at = datetime.datetime.now()
            db.session.commit()
            logger.info(f"Updated conversation {conversation_id}")
            return conversation
        logger.error(f"Conversation {conversation_id} not found")
        return None

    def get_conversations_for_collection(
        self, collection_id: int
    ) -> List[Conversation]:
        """Get all conversations for a collection, ordered by most recent."""
        return (
            Conversation.query.filter_by(collection_id=collection_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        citations: list = None,
        evaluation: dict = None,
        model_name: str = None,
        provider: str = None,
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_name=model_name,
            provider=provider,
        )
        if citations:
            message.citations = citations
        if evaluation:
            message.evaluation = evaluation

        db.session.add(message)

        # Update conversation title from first user message
        logger.debug("add_message conversation_id: %s", conversation_id)
        conversation = db.session.get(Conversation, conversation_id)
        logger.debug("add_message conversation: %s", conversation)
        logger.debug("add_message role: %s", role)
        if conversation and role == "user":
            logger.debug("add_message checking msg_count")
            msg_count = Message.query.filter_by(
                conversation_id=conversation_id
            ).count()
            logger.debug("add_message msg_count: %s", msg_count)
            if msg_count == 1:
                logger.debug("add_message setting conversation title")
                # First message - use it as the title (truncated)
                conversation.title = content[:100] + ("..." if len(content) > 100 else "")

        db.session.commit()
        return message

    def get_chat_history(
        self, conversation_id: int, window: int = None
    ) -> List[Dict[str, str]]:
        """
        Get recent chat history for context windowing.

        Returns the last N messages as simple dicts for LLM context.
        """
        window = window or self.history_window
        messages = (
            Message.query.filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.desc())
            .limit(window)
            .all()
        )
        # Reverse to chronological order
        messages.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def update_message_evaluation(
        self, message_id: int, evaluation: dict
    ) -> Optional[Message]:
        """Update the evaluation scores on a message."""
        message = db.session.get(Message, message_id)
        if message:
            message.evaluation = evaluation
            db.session.commit()
        return message

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conversation = db.session.get(Conversation, conversation_id)
        if conversation:
            db.session.delete(conversation)
            db.session.commit()
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        return False

