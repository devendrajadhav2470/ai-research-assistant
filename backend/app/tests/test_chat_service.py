"""Tests for ChatService: conversation CRUD, message management, and chat history.

All database interactions use the in-memory SQLite backend.  The ``user_context``
fixture ensures ``flask.g.user`` is populated for operations that read user id.
"""

import pytest
from unittest.mock import MagicMock

from app.extensions import db
from app.models.chat import Conversation, Message
from app.services.chat_service import ChatService
from app.tests.conftest import SAMPLE_USER_PAYLOAD


@pytest.fixture
def chat_service():
    """A plain ChatService with default history window."""
    return ChatService()


# ── create_conversation ────────────────────────────────────────────────────

class TestCreateConversation:
    """Tests for ChatService.create_conversation."""

    def test_creates_conversation_with_defaults(
        self, sample_collection, user_context, chat_service
    ):
        """A conversation is created with the default title."""
        conv = chat_service.create_conversation(sample_collection.id)
        assert conv.id is not None
        assert conv.title == "New Conversation"
        assert conv.collection_id == sample_collection.id

    def test_creates_conversation_with_custom_title(
        self, sample_collection, user_context, chat_service
    ):
        """A custom title is stored correctly."""
        conv = chat_service.create_conversation(
            sample_collection.id, title="My Chat"
        )
        assert conv.title == "My Chat"


# ── get_conversation ──────────────────────────────────────────────────────

class TestGetConversation:
    """Tests for ChatService.get_conversation."""

    def test_returns_conversation_when_found(
        self, sample_conversation, chat_service
    ):
        """Returns the Conversation object for a valid id."""
        result = chat_service.get_conversation(sample_conversation.id)
        assert result is not None
        assert result.id == sample_conversation.id

    def test_returns_none_when_not_found(self, app, chat_service):
        """Returns None for a non-existent conversation id."""
        assert chat_service.get_conversation(99999) is None


# ── get_conversation_messages ─────────────────────────────────────────────

class TestGetConversationMessages:
    """Tests for ChatService.get_conversation_messages."""

    def test_returns_messages_ordered_desc(
        self, sample_conversation, chat_service, user_context
    ):
        """Messages are returned in descending id order."""
        for i in range(3):
            chat_service.add_message(
                sample_conversation.id, role="user", content=f"msg {i}"
            )
        msgs = chat_service.get_conversation_messages(
            sample_conversation.id, limit=10
        )
        assert len(msgs) == 3
        assert msgs[0].id > msgs[1].id > msgs[2].id

    def test_respects_before_id(
        self, sample_conversation, chat_service, user_context
    ):
        """Only messages with id < before_id are returned."""
        for i in range(5):
            chat_service.add_message(
                sample_conversation.id, role="user", content=f"msg {i}"
            )
        all_msgs = chat_service.get_conversation_messages(
            sample_conversation.id, limit=10
        )
        mid_id = all_msgs[2].id
        older = chat_service.get_conversation_messages(
            sample_conversation.id, limit=10, before_id=mid_id
        )
        assert all(m.id < mid_id for m in older)

    def test_respects_limit(
        self, sample_conversation, chat_service, user_context
    ):
        """No more than ``limit`` messages are returned."""
        for i in range(5):
            chat_service.add_message(
                sample_conversation.id, role="user", content=f"msg {i}"
            )
        msgs = chat_service.get_conversation_messages(
            sample_conversation.id, limit=2
        )
        assert len(msgs) == 2


# ── update_conversation ──────────────────────────────────────────────────

class TestUpdateConversation:
    """Tests for ChatService.update_conversation."""

    def test_updates_title(self, sample_conversation, chat_service):
        """Title is updated and persisted."""
        updated = chat_service.update_conversation(
            sample_conversation.id, {"title": "Renamed"}
        )
        assert updated.title == "Renamed"

    def test_returns_none_for_missing(self, app, chat_service):
        """Returns None for a non-existent conversation."""
        assert chat_service.update_conversation(99999, {"title": "X"}) is None


# ── get_conversations_for_collection ─────────────────────────────────────

class TestGetConversationsForCollection:
    """Tests for ChatService.get_conversations_for_collection."""

    def test_returns_conversations_for_collection(
        self, sample_collection, sample_conversation, chat_service
    ):
        """All conversations belonging to the collection are returned."""
        convs = chat_service.get_conversations_for_collection(
            sample_collection.id
        )
        assert len(convs) >= 1
        assert convs[0].id == sample_conversation.id


# ── add_message ──────────────────────────────────────────────────────────

class TestAddMessage:
    """Tests for ChatService.add_message."""

    def test_adds_user_message(
        self, sample_conversation, chat_service, user_context
    ):
        """A user message is persisted with correct role and content."""
        msg = chat_service.add_message(
            sample_conversation.id, role="user", content="Hello"
        )
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_adds_assistant_message_with_citations(
        self, sample_conversation, chat_service, user_context
    ):
        """An assistant message stores citations via the JSON property."""
        cites = [{"source": "doc.pdf", "page_number": 1}]
        msg = chat_service.add_message(
            sample_conversation.id,
            role="assistant",
            content="Answer",
            citations=cites,
            model_name="gpt-4o",
            provider="openai",
        )
        assert msg.citations == cites
        assert msg.model_name == "gpt-4o"

    def test_first_user_message_sets_conversation_title(
        self, sample_collection, user_context, chat_service
    ):
        """The conversation title is derived from the first user message."""
        conv = chat_service.create_conversation(sample_collection.id)
        chat_service.add_message(conv.id, role="user", content="What is RAG?")
        refreshed = db.session.get(Conversation, conv.id)
        assert "What is RAG?" in refreshed.title

    def test_long_first_message_truncates_title(
        self, sample_collection, user_context, chat_service
    ):
        """Titles longer than 100 chars are truncated with ellipsis."""
        conv = chat_service.create_conversation(sample_collection.id)
        long_msg = "A" * 150
        chat_service.add_message(conv.id, role="user", content=long_msg)
        refreshed = db.session.get(Conversation, conv.id)
        assert refreshed.title.endswith("...")
        assert len(refreshed.title) == 103  # 100 chars + "..."


# ── get_chat_history ─────────────────────────────────────────────────────

class TestGetChatHistory:
    """Tests for ChatService.get_chat_history."""

    def test_returns_list_of_dicts(
        self, sample_conversation, chat_service, user_context
    ):
        """Returned items are simple {role, content} dicts."""
        chat_service.add_message(
            sample_conversation.id, role="user", content="Hi"
        )
        history = chat_service.get_chat_history(sample_conversation.id)
        assert isinstance(history, list)
        assert history[0] == {"role": "user", "content": "Hi"}

    def test_respects_window_size(
        self, sample_conversation, chat_service, user_context
    ):
        """Only the most recent ``window`` messages are returned."""
        for i in range(15):
            chat_service.add_message(
                sample_conversation.id, role="user", content=f"msg {i}"
            )
        history = chat_service.get_chat_history(
            sample_conversation.id, window=3
        )
        assert len(history) == 3


# ── update_message_evaluation ────────────────────────────────────────────

class TestUpdateMessageEvaluation:
    """Tests for ChatService.update_message_evaluation."""

    def test_stores_evaluation(self, sample_message, chat_service):
        """Evaluation dict is persisted via the JSON property."""
        evaluation = {"overall_score": 4.5, "faithfulness": {"score": 5}}
        result = chat_service.update_message_evaluation(
            sample_message.id, evaluation
        )
        assert result is not None
        assert result.evaluation["overall_score"] == 4.5

    def test_returns_none_for_missing_message(self, app, chat_service):
        """Returns None when the message does not exist."""
        result = chat_service.update_message_evaluation(99999, {})
        assert result is None


# ── delete_conversation ──────────────────────────────────────────────────

class TestDeleteConversation:
    """Tests for ChatService.delete_conversation."""

    def test_deletes_existing_conversation(
        self, sample_conversation, chat_service
    ):
        """Returns True and removes the conversation from the database."""
        assert chat_service.delete_conversation(sample_conversation.id) is True
        assert db.session.get(Conversation, sample_conversation.id) is None

    def test_returns_false_for_missing(self, app, chat_service):
        """Returns False when the conversation does not exist."""
        assert chat_service.delete_conversation(99999) is False
