"""Tests for the collections API blueprint: CRUD operations.

All endpoints are protected by ``token_required``; the ``mock_auth`` fixture
bypasses authentication so we can test the business logic directly.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models.document import Collection
from app.tests.conftest import SAMPLE_USER_PAYLOAD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JSON_CT = {"Content-Type": "application/json"}


@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed headers for every test in this module."""
    return auth_headers


# ── GET /api/collections ─────────────────────────────────────────────────

class TestListCollections:
    """Tests for GET /api/collections."""

    def test_empty_list(self, client, headers):
        """Returns an empty JSON array when no collections exist."""
        resp = client.get("/api/collections", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_existing(self, client, headers, sample_collection):
        """Returns all existing collections."""
        resp = client.get("/api/collections", headers=headers)
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Collection"


# ── POST /api/collections ────────────────────────────────────────────────

class TestCreateCollection:
    """Tests for POST /api/collections."""

    def test_creates_collection(self, client, headers, sample_user):
        """Valid name creates a collection and returns 201."""
        resp = client.post(
            "/api/collections", headers=headers,
            data=json.dumps({"name": "New Coll", "description": "desc"}),
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "New Coll"

    def test_missing_name_returns_400(self, client, headers):
        """No name field returns 400."""
        resp = client.post(
            "/api/collections", headers=headers,
            data=json.dumps({"description": "no name"}),
        )
        assert resp.status_code == 400

    def test_empty_body_returns_400(self, client, headers):
        """Empty JSON body returns 400."""
        resp = client.post(
            "/api/collections", headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 400


# ── GET /api/collections/<id> ────────────────────────────────────────────

class TestGetCollection:
    """Tests for GET /api/collections/<id>."""

    def test_found(self, client, headers, sample_collection):
        """Returns 200 and the collection dict."""
        resp = client.get(
            f"/api/collections/{sample_collection.id}", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["id"] == sample_collection.id

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent id."""
        resp = client.get("/api/collections/99999", headers=headers)
        assert resp.status_code == 404


# ── PUT /api/collections/<id> ────────────────────────────────────────────

class TestUpdateCollection:
    """Tests for PUT /api/collections/<id>."""

    def test_update_name(self, client, headers, sample_collection):
        """Name is updated and returned."""
        resp = client.put(
            f"/api/collections/{sample_collection.id}", headers=headers,
            data=json.dumps({"name": "Renamed"}),
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Renamed"

    def test_update_description(self, client, headers, sample_collection):
        """Description is updated independently of name."""
        resp = client.put(
            f"/api/collections/{sample_collection.id}", headers=headers,
            data=json.dumps({"description": "Updated desc"}),
        )
        assert resp.status_code == 200
        assert resp.get_json()["description"] == "Updated desc"

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent collection."""
        resp = client.put(
            "/api/collections/99999", headers=headers,
            data=json.dumps({"name": "X"}),
        )
        assert resp.status_code == 404


# ── DELETE /api/collections/<id> ─────────────────────────────────────────

class TestDeleteCollection:
    """Tests for DELETE /api/collections/<id>."""

    @patch("app.api.collections.BM25Index")
    @patch("app.api.collections.VectorStore")
    def test_deletes_collection(self, mock_vs, mock_bm25, client, headers,
                                sample_collection):
        """Returns success message and removes from DB."""
        coll_id = sample_collection.id
        resp = client.delete(
            f"/api/collections/{coll_id}", headers=headers,
        )
        assert resp.status_code == 200
        assert b"deleted" in resp.data.lower()
        assert db.session.get(Collection, coll_id) is None

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent collection."""
        resp = client.delete("/api/collections/99999", headers=headers)
        assert resp.status_code == 404

    @patch("app.api.collections.BM25Index")
    @patch("app.api.collections.VectorStore")
    def test_vector_cleanup_failure_is_swallowed(
        self, mock_vs, mock_bm25, client, headers, sample_collection,
    ):
        """Errors during vector/BM25 cleanup do not prevent deletion."""
        mock_vs.return_value.delete_collection.side_effect = RuntimeError("fail")
        coll_id = sample_collection.id
        resp = client.delete(f"/api/collections/{coll_id}", headers=headers)
        assert resp.status_code == 200
