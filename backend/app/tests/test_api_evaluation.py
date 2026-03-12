"""Tests for the evaluation API blueprint: evaluate and get evaluation."""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models.chat import Message


@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed headers."""
    return auth_headers


# ── POST /api/evaluation/evaluate/<message_id> ──────────────────────────

class TestEvaluateMessage:
    """Tests for POST /api/evaluation/evaluate/<message_id>."""

    @patch("app.api.evaluation.ChatService")
    @patch("app.api.evaluation.RAGPipeline")
    @patch("app.api.evaluation.HybridRetriever")
    def test_successful_evaluation(
        self, mock_retriever_cls, mock_rag_cls, mock_cs_cls,
        client, headers, sample_message, sample_conversation,
    ):
        """Evaluating an assistant message returns evaluation scores."""
        # Create a preceding user message
        user_msg = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="What is ML?",
        )
        db.session.add(user_msg)
        db.session.commit()

        mock_retriever_cls.return_value.retrieve.return_value = []
        mock_rag_cls.return_value.evaluate_response.return_value = {
            "overall_score": 4.0,
        }

        resp = client.post(
            f"/api/evaluation/evaluate/{sample_message.id}",
            headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 200
        assert resp.get_json()["evaluation"]["overall_score"] == 4.0

    def test_message_not_found(self, client, headers):
        """Returns 404 when message does not exist."""
        resp = client.post(
            "/api/evaluation/evaluate/99999",
            headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 404

    def test_user_message_returns_400(self, client, headers,
                                      sample_conversation):
        """Evaluating a user message returns 400."""
        msg = Message(
            conversation_id=sample_conversation.id,
            role="user", content="question",
        )
        db.session.add(msg)
        db.session.commit()

        resp = client.post(
            f"/api/evaluation/evaluate/{msg.id}",
            headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 400

    @patch("app.api.evaluation.ChatService")
    @patch("app.api.evaluation.RAGPipeline")
    @patch("app.api.evaluation.HybridRetriever")
    def test_no_user_message_returns_400(
        self, mock_ret, mock_rag, mock_cs,
        client, headers, sample_conversation,
    ):
        """If there is no preceding user message, returns 400."""
        assistant_msg = Message(
            conversation_id=sample_conversation.id,
            role="assistant", content="answer",
        )
        db.session.add(assistant_msg)
        db.session.commit()

        resp = client.post(
            f"/api/evaluation/evaluate/{assistant_msg.id}",
            headers=headers, data=json.dumps({}),
        )
        assert resp.status_code == 400

    @patch("app.api.evaluation.ChatService")
    @patch("app.api.evaluation.RAGPipeline")
    @patch("app.api.evaluation.HybridRetriever")
    def test_passes_provider_and_model(
        self, mock_ret_cls, mock_rag_cls, mock_cs_cls,
        client, headers, sample_message, sample_conversation,
    ):
        """Provider and model_name are forwarded to the RAG pipeline."""
        user_msg = Message(
            conversation_id=sample_conversation.id,
            role="user", content="Q",
        )
        db.session.add(user_msg)
        db.session.commit()

        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rag_cls.return_value.evaluate_response.return_value = {
            "overall_score": 3.0,
        }

        resp = client.post(
            f"/api/evaluation/evaluate/{sample_message.id}",
            headers=headers,
            data=json.dumps({"provider": "anthropic",
                             "model_name": "claude-sonnet-4-20250514"}),
        )
        assert resp.status_code == 200
        call_kwargs = mock_rag_cls.return_value.evaluate_response.call_args.kwargs
        assert call_kwargs["provider"] == "anthropic"


# ── GET /api/evaluation/message/<message_id> ─────────────────────────────

class TestGetEvaluation:
    """Tests for GET /api/evaluation/message/<message_id>."""

    def test_returns_evaluation(self, client, headers, sample_message):
        """Returns the stored evaluation for a message."""
        sample_message.evaluation = {"overall_score": 4.5}
        db.session.commit()

        resp = client.get(
            f"/api/evaluation/message/{sample_message.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["evaluation"]["overall_score"] == 4.5

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent message."""
        resp = client.get(
            "/api/evaluation/message/99999", headers=headers,
        )
        assert resp.status_code == 404
