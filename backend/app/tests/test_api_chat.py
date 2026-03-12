"""Tests for the chat API blueprint: conversation CRUD, query, streaming, model listing.

RAGPipeline, ChatService, and LLMService are mocked at the API boundary.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models.chat import Conversation, Message


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed JSON headers."""
    return auth_headers


# ── GET /api/chat/conversations/collection/<id> ──────────────────────────

class TestListConversations:
    """Tests for GET /api/chat/conversations/collection/<collection_id>."""

    def test_returns_conversations(self, client, headers, sample_conversation):
        """Returns conversations for a valid collection."""
        cid = sample_conversation.collection_id
        resp = client.get(
            f"/api/chat/conversations/collection/{cid}", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_collection_not_found(self, client, headers):
        """Returns 404 for a non-existent collection."""
        resp = client.get(
            "/api/chat/conversations/collection/99999", headers=headers,
        )
        assert resp.status_code == 404


# ── POST /api/chat/conversations ─────────────────────────────────────────

class TestCreateConversation:
    """Tests for POST /api/chat/conversations."""

    def test_creates_conversation(self, client, headers, sample_collection):
        """Valid collection_id creates a conversation and returns 201."""
        resp = client.post(
            "/api/chat/conversations", headers=headers,
            data=json.dumps({"collection_id": sample_collection.id}),
        )
        assert resp.status_code == 201
        assert resp.get_json()["title"] == "New Conversation"

    def test_custom_title(self, client, headers, sample_collection):
        """A custom title is stored correctly."""
        resp = client.post(
            "/api/chat/conversations", headers=headers,
            data=json.dumps({
                "collection_id": sample_collection.id,
                "title": "My Chat",
            }),
        )
        assert resp.get_json()["title"] == "My Chat"

    def test_missing_collection_id(self, client, headers):
        """Missing collection_id returns 400."""
        resp = client.post(
            "/api/chat/conversations", headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 400

    def test_nonexistent_collection(self, client, headers):
        """A collection_id that doesn't exist returns 404."""
        resp = client.post(
            "/api/chat/conversations", headers=headers,
            data=json.dumps({"collection_id": 99999}),
        )
        assert resp.status_code == 404


# ── GET /api/chat/conversations/<id> ─────────────────────────────────────

class TestGetConversation:
    """Tests for GET /api/chat/conversations/<conversation_id>."""

    def test_returns_conversation(self, client, headers, sample_conversation):
        """Returns the conversation with messages list."""
        resp = client.get(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["id"] == sample_conversation.id
        assert "messages" in body
        assert "hasOlder" in body

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent conversation."""
        resp = client.get(
            "/api/chat/conversations/99999", headers=headers,
        )
        assert resp.status_code == 404


# ── PATCH /api/chat/conversations/<id> ───────────────────────────────────

class TestUpdateConversation:
    """Tests for PATCH /api/chat/conversations/<conversation_id>."""

    def test_updates_title(self, client, headers, sample_conversation):
        """Title is updated and returned."""
        resp = client.patch(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=headers,
            data=json.dumps({"title": "Renamed Chat"}),
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Renamed Chat"

    def test_missing_title(self, client, headers, sample_conversation):
        """Missing title returns 400."""
        resp = client.patch(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 400

    def test_empty_body(self, client, headers, sample_conversation):
        """No JSON body returns 400."""
        resp = client.patch(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=headers, data="",
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── DELETE /api/chat/conversations/<id> ──────────────────────────────────

class TestDeleteConversation:
    """Tests for DELETE /api/chat/conversations/<conversation_id>."""

    def test_deletes_conversation(self, client, headers, sample_conversation):
        """Returns success message."""
        resp = client.delete(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent conversation."""
        resp = client.delete(
            "/api/chat/conversations/99999", headers=headers,
        )
        assert resp.status_code == 404


# ── POST /api/chat/query ─────────────────────────────────────────────────

class TestQuery:
    """Tests for POST /api/chat/query."""

    @patch("app.api.chat.RAGPipeline")
    @patch("app.api.chat.ChatService")
    def test_successful_query(self, mock_cs_cls, mock_rag_cls, client,
                              headers, sample_collection):
        """A valid query returns the RAG answer."""
        mock_rag = mock_rag_cls.return_value
        mock_rag.query.return_value = {
            "answer": "42",
            "citations": [],
            "chunks": [],
            "model_info": {"provider": "openai", "model": "gpt-4o"},
        }
        mock_cs = mock_cs_cls.return_value
        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.collection_id = sample_collection.id
        mock_cs.create_conversation.return_value = mock_conv
        mock_msg = MagicMock()
        mock_msg.id = 10
        mock_cs.add_message.return_value = mock_msg

        resp = client.post(
            "/api/chat/query", headers=headers,
            data=json.dumps({
                "question": "What is the answer?",
                "collection_id": sample_collection.id,
            }),
        )
        assert resp.status_code == 200
        assert resp.get_json()["answer"] == "42"

    def test_missing_question(self, client, headers, sample_collection):
        """Missing question returns 400."""
        resp = client.post(
            "/api/chat/query", headers=headers,
            data=json.dumps({"collection_id": sample_collection.id}),
        )
        assert resp.status_code == 400

    def test_question_too_long(self, client, headers, sample_collection):
        """A question exceeding MAX_QUESTION_LENGTH returns 400."""
        resp = client.post(
            "/api/chat/query", headers=headers,
            data=json.dumps({
                "question": "A" * 600,
                "collection_id": sample_collection.id,
            }),
        )
        assert resp.status_code == 400

    def test_missing_collection_id(self, client, headers):
        """Missing collection_id returns 400."""
        resp = client.post(
            "/api/chat/query", headers=headers,
            data=json.dumps({"question": "Hi"}),
        )
        assert resp.status_code == 400

    def test_nonexistent_collection(self, client, headers):
        """A non-existent collection_id returns 404."""
        resp = client.post(
            "/api/chat/query", headers=headers,
            data=json.dumps({"question": "Hi", "collection_id": 99999}),
        )
        assert resp.status_code == 404

    def test_empty_body(self, client, headers):
        """No body returns 400."""
        resp = client.post(
            "/api/chat/query", headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 400


# ── POST /api/chat/query/stream ──────────────────────────────────────────

class TestQueryStream:
    """Tests for POST /api/chat/query/stream (SSE)."""

    @patch("app.api.chat.RAGPipeline")
    @patch("app.api.chat.ChatService")
    def test_stream_returns_sse(self, mock_cs_cls, mock_rag_cls, client,
                                headers, sample_collection):
        """The streaming endpoint returns text/event-stream."""
        mock_rag = mock_rag_cls.return_value
        mock_rag.query_stream.return_value = iter([
            {"type": "chunks", "data": []},
            {"type": "token", "data": "Hello"},
            {"type": "done", "data": {
                "answer": "Hello",
                "citations": [],
                "model_info": {"provider": "openai", "model": "gpt-4o"},
            }},
        ])
        mock_cs = mock_cs_cls.return_value
        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.collection_id = sample_collection.id
        mock_cs.create_conversation.return_value = mock_conv
        mock_msg = MagicMock()
        mock_msg.id = 10
        mock_cs.add_message.return_value = mock_msg

        resp = client.post(
            "/api/chat/query/stream", headers=headers,
            data=json.dumps({
                "question": "Hi",
                "collection_id": sample_collection.id,
            }),
        )
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/event-stream")

        raw = resp.data.decode()
        assert "event: chunks" in raw
        assert "event: done" in raw

    def test_stream_missing_question(self, client, headers, sample_collection):
        """Missing question returns 400."""
        resp = client.post(
            "/api/chat/query/stream", headers=headers,
            data=json.dumps({"collection_id": sample_collection.id}),
        )
        assert resp.status_code == 400


# ── GET /api/chat/models ─────────────────────────────────────────────────

class TestListModels:
    """Tests for GET /api/chat/models."""

    @patch("app.api.chat.LLMService")
    def test_returns_models(self, mock_llm_cls, client, headers):
        """Returns the available models dict."""
        mock_llm_cls.get_available_models.return_value = {
            "openai": [{"id": "gpt-4o", "name": "GPT-4o"}]
        }
        resp = client.get("/api/chat/models", headers=headers)
        assert resp.status_code == 200
        assert "openai" in resp.get_json()
