"""Tests for SQLAlchemy models: User, Collection, Document, Chunk, Conversation, Message.

Validates ``to_dict()`` serialisation, JSON-backed property getters/setters on
Message (citations, evaluation), and Conversation's optional message inclusion.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.extensions import db
from app.models.user import User, Status, UserType
from app.models.document import Collection, Document, Chunk
from app.models.chat import Conversation, Message


# ── User model ─────────────────────────────────────────────────────────────

class TestUserModel:
    """Tests for the User SQLAlchemy model."""

    def test_user_creation_sets_defaults(self, app, sample_user):
        """Verify that default fields are populated after insert."""
        user = db.session.get(User, sample_user.id)
        assert user is not None
        assert user.email == sample_user.email
        assert user.status == Status.ACTIVE
        assert user.mfa_enabled is False
        assert user.created_at is not None

    def test_user_status_enum_values(self):
        """Verify Status enum members."""
        assert Status.ACTIVE.value == "active"
        assert Status.DISABLED.value == "disabled"
        assert Status.LOCKED.value == "locked"

    def test_user_type_enum_values(self):
        """Verify UserType enum members."""
        assert UserType.GUEST.value == "guest"
        assert UserType.PERMANENT.value == "permanent"


# ── Collection model ───────────────────────────────────────────────────────

class TestCollectionModel:
    """Tests for Collection.to_dict()."""

    def test_to_dict_returns_expected_keys(self, sample_collection):
        """Verify all expected keys are present in serialised output."""
        data = sample_collection.to_dict()
        expected_keys = {"id", "name", "description", "document_count",
                         "created_at", "updated_at"}
        assert expected_keys == set(data.keys())

    def test_to_dict_document_count_zero(self, sample_collection):
        """A fresh collection has zero documents."""
        assert sample_collection.to_dict()["document_count"] == 0

    def test_to_dict_timestamps_are_iso(self, sample_collection):
        """Timestamps should be ISO-8601 strings."""
        data = sample_collection.to_dict()
        datetime.fromisoformat(data["created_at"])


# ── Document model ─────────────────────────────────────────────────────────

class TestDocumentModel:
    """Tests for Document.to_dict()."""

    def test_to_dict_returns_expected_keys(self, sample_document):
        """Verify the serialised key set."""
        data = sample_document.to_dict()
        expected = {"id", "collection_id", "filename", "file_size",
                    "page_count", "chunk_count", "status", "error_message",
                    "created_at"}
        assert expected == set(data.keys())

    def test_to_dict_status_ready(self, sample_document):
        """Document status should match the fixture value."""
        assert sample_document.to_dict()["status"] == "ready"

    def test_to_dict_error_message_none(self, sample_document):
        """Error message is None for a healthy document."""
        assert sample_document.to_dict()["error_message"] is None


# ── Chunk model ────────────────────────────────────────────────────────────

class TestChunkModel:
    """Tests for Chunk.to_dict() using a real DB row."""

    def test_to_dict_returns_expected_keys(self, sample_document):
        """Insert a Chunk and verify its serialised form."""
        chunk = Chunk(
            id="abc123hash",
            document_id=sample_document.id,
            collection_id=sample_document.collection_id,
            content="Some chunk text.",
            page_number=1,
            chunk_index=0,
            metadata_json='{"source": "test.pdf"}',
        )
        db.session.add(chunk)
        db.session.commit()

        data = chunk.to_dict()
        assert data["id"] == "abc123hash"
        assert data["content"] == "Some chunk text."
        assert data["page_number"] == 1
        assert data["chunk_index"] == 0


# ── Conversation model ─────────────────────────────────────────────────────

class TestConversationModel:
    """Tests for Conversation.to_dict() with and without messages."""

    def test_to_dict_without_messages(self, sample_conversation):
        """Default serialisation excludes messages."""
        data = sample_conversation.to_dict(include_messages=False)
        assert "messages" not in data
        assert data["title"] == "Test Conversation"

    def test_to_dict_with_messages(self, sample_conversation):
        """When include_messages=True, a messages list is present."""
        data = sample_conversation.to_dict(include_messages=True)
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_to_dict_contains_message_count(self, sample_conversation):
        """message_count reflects the actual number of related messages."""
        assert sample_conversation.to_dict()["message_count"] == 0


# ── Message model ──────────────────────────────────────────────────────────

class TestMessageModel:
    """Tests for Message serialisation and JSON-backed properties."""

    def test_to_dict_returns_expected_keys(self, sample_message):
        """Verify the serialised key set."""
        data = sample_message.to_dict()
        expected = {"id", "conversation_id", "role", "content", "citations",
                    "evaluation", "model_name", "provider", "created_at"}
        assert expected == set(data.keys())

    def test_citations_property_getter_valid_json(self, sample_message):
        """citations getter deserialises a valid JSON array."""
        sample_message.citations_json = json.dumps([{"source": "a.pdf"}])
        assert sample_message.citations == [{"source": "a.pdf"}]

    def test_citations_property_getter_empty(self, sample_message):
        """citations getter returns [] when json is empty string."""
        sample_message.citations_json = ""
        assert sample_message.citations == []

    def test_citations_property_getter_invalid_json(self, sample_message):
        """citations getter returns [] for malformed JSON."""
        sample_message.citations_json = "not-json"
        assert sample_message.citations == []

    def test_citations_property_setter(self, sample_message):
        """citations setter serialises a list to JSON."""
        sample_message.citations = [{"source": "b.pdf", "page_number": 3}]
        assert json.loads(sample_message.citations_json) == [
            {"source": "b.pdf", "page_number": 3}
        ]

    def test_citations_setter_none(self, sample_message):
        """citations setter stores '[]' when value is None."""
        sample_message.citations = None
        assert sample_message.citations_json == "[]"

    def test_evaluation_property_getter_valid_json(self, sample_message):
        """evaluation getter deserialises a valid JSON object."""
        sample_message.evaluation_json = json.dumps({"overall_score": 4.0})
        assert sample_message.evaluation == {"overall_score": 4.0}

    def test_evaluation_property_getter_empty(self, sample_message):
        """evaluation getter returns {} for empty string."""
        sample_message.evaluation_json = ""
        assert sample_message.evaluation == {}

    def test_evaluation_property_getter_invalid_json(self, sample_message):
        """evaluation getter returns {} for malformed JSON."""
        sample_message.evaluation_json = "{bad"
        assert sample_message.evaluation == {}

    def test_evaluation_property_setter(self, sample_message):
        """evaluation setter serialises a dict to JSON."""
        sample_message.evaluation = {"overall_score": 3.5, "error": False}
        stored = json.loads(sample_message.evaluation_json)
        assert stored["overall_score"] == 3.5

    def test_evaluation_setter_none(self, sample_message):
        """evaluation setter stores '{}' when value is None."""
        sample_message.evaluation = None
        assert sample_message.evaluation_json == "{}"
