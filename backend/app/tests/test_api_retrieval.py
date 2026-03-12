"""Tests for the retrieval API blueprint: POST /api/retrieval/search."""

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed headers."""
    return auth_headers


class TestSearchChunks:
    """Tests for POST /api/retrieval/search."""

    @patch("app.api.retrieval.HybridRetriever")
    def test_successful_search(self, mock_ret_cls, client, headers,
                               sample_collection):
        """A valid search returns chunk results."""
        mock_ret_cls.return_value.retrieve.return_value = [
            {"content": "result 1", "score": 0.9},
        ]
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({
                "collection_id": sample_collection.id,
                "question": "What is RAG?",
            }),
        )
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_missing_collection_id(self, client, headers):
        """Missing collection_id returns 400."""
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({"question": "Hi"}),
        )
        assert resp.status_code == 400

    def test_missing_question(self, client, headers, sample_collection):
        """Missing question returns 400."""
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({"collection_id": sample_collection.id}),
        )
        assert resp.status_code == 400

    def test_collection_not_found(self, client, headers):
        """Non-existent collection_id returns 404."""
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({"collection_id": 99999, "question": "Q"}),
        )
        assert resp.status_code == 404

    @patch("app.api.retrieval.HybridRetriever")
    def test_question_too_long(self, mock_ret_cls, client, headers,
                               sample_collection):
        """A question exceeding MAX_QUESTION_LENGTH returns 400."""
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({
                "collection_id": sample_collection.id,
                "question": "A" * 600,
            }),
        )
        assert resp.status_code == 400

    @patch("app.api.retrieval.HybridRetriever")
    def test_whitespace_normalised(self, mock_ret_cls, client, headers,
                                   sample_collection):
        """Excess whitespace in the question is normalised."""
        mock_ret_cls.return_value.retrieve.return_value = []
        resp = client.post(
            "/api/retrieval/search", headers=headers,
            data=json.dumps({
                "collection_id": sample_collection.id,
                "question": "  hello   world  ",
            }),
        )
        assert resp.status_code == 200
        call_kwargs = mock_ret_cls.return_value.retrieve.call_args.kwargs
        assert call_kwargs["query"] == "hello world"
