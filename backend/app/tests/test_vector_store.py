"""Tests for VectorStore: ChromaDB-backed vector operations.

The ChromaDB HttpClient is mocked via ``current_app.extensions['chroma_client']``
which is a MagicMock injected by the test app fixture.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.services.vector_store import VectorStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chroma(app):
    """Return the mocked chroma_client from the test app."""
    from flask import current_app
    return current_app.extensions["chroma_client"]


@pytest.fixture
def store(app):
    """A VectorStore wired to the mocked chroma_client."""
    return VectorStore()


COLLECTION_ID = 7
COLLECTION_NAME = "collection_7"


# ── _get_collection_name ─────────────────────────────────────────────────

class TestGetCollectionName:
    """Tests for VectorStore._get_collection_name."""

    def test_format(self, store):
        """Name follows 'collection_{id}' pattern."""
        assert store._get_collection_name(42) == "collection_42"


# ── add_vectors ──────────────────────────────────────────────────────────

class TestAddVectors:
    """Tests for VectorStore.add_vectors."""

    def test_delegates_to_chroma(self, store, chroma):
        """add_vectors calls chroma_collection.add with correct arguments."""
        mock_coll = MagicMock()
        chroma.create_collection.return_value = mock_coll

        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        ids = ["id1", "id2"]
        meta = [{"doc": 1}, {"doc": 2}]

        store.add_vectors(COLLECTION_ID, ids, embeddings, meta)
        mock_coll.add.assert_called_once_with(
            ids=ids, embeddings=embeddings, metadatas=meta,
        )

    def test_empty_embeddings_skipped(self, store, chroma):
        """When embeddings is empty, chroma add is not called."""
        mock_coll = MagicMock()
        chroma.create_collection.return_value = mock_coll
        store.add_vectors(COLLECTION_ID, [], [], [])
        mock_coll.add.assert_not_called()

    def test_lazy_collection_creation(self, store, chroma):
        """The chroma collection is created on first add_vectors call."""
        mock_coll = MagicMock()
        chroma.create_collection.return_value = mock_coll
        store.add_vectors(COLLECTION_ID, ["id1"], [[0.1]], [{"k": "v"}])
        chroma.create_collection.assert_called()

    def test_switches_collection_when_id_changes(self, store, chroma):
        """If collection_id changes, the collection is re-loaded."""
        coll_a = MagicMock()
        coll_a.name = "collection_1"
        coll_b = MagicMock()
        coll_b.name = "collection_2"
        chroma.create_collection.side_effect = [coll_a, coll_b]

        store.add_vectors(1, ["id1"], [[0.1]], [{}])
        store.add_vectors(2, ["id2"], [[0.2]], [{}])
        assert chroma.create_collection.call_count == 2


# ── search ───────────────────────────────────────────────────────────────

class TestSearch:
    """Tests for VectorStore.search."""

    def test_returns_metadata_score_tuples(self, store, chroma):
        """search returns a list of (metadata, score) tuples."""
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.5]],
            "metadatas": [[{"doc": 1}, {"doc": 2}]],
        }
        chroma.get_collection.return_value = mock_coll

        query_emb = np.random.randn(768).astype(np.float32)
        results = store.search(COLLECTION_ID, query_emb, top_k=5)
        assert len(results) == 2
        assert isinstance(results[0], tuple)
        assert results[0][0] == {"doc": 1}

    def test_collection_not_found_returns_empty(self, store, chroma):
        """If get_collection raises, an empty list is returned."""
        chroma.get_collection.side_effect = Exception("not found")
        query_emb = np.random.randn(768).astype(np.float32)
        assert store.search(COLLECTION_ID, query_emb) == []

    def test_score_transformation(self, store, chroma):
        """Scores are transformed via the sigmoid-like function."""
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.0]],
            "metadatas": [[{"doc": 1}]],
        }
        chroma.get_collection.return_value = mock_coll
        results = store.search(COLLECTION_ID, np.zeros(768, dtype=np.float32))
        assert 0 < results[0][1] < 1


# ── delete_collection ────────────────────────────────────────────────────

class TestDeleteCollection:
    """Tests for VectorStore.delete_collection."""

    def test_delegates_to_chroma(self, store, chroma):
        """delete_collection calls chroma_client.delete_collection."""
        store.delete_collection(COLLECTION_ID)
        chroma.delete_collection.assert_called_once_with(COLLECTION_NAME)

    def test_nonexistent_collection_no_error(self, store, chroma):
        """Deleting a non-existent collection does not raise."""
        chroma.delete_collection.side_effect = Exception("missing")
        store.delete_collection(COLLECTION_ID)

    def test_clears_cached_collection(self, store, chroma):
        """If the deleted collection was cached, the cache is cleared."""
        mock_coll = MagicMock()
        mock_coll.name = COLLECTION_NAME
        chroma.create_collection.return_value = mock_coll
        store.add_vectors(COLLECTION_ID, ["id"], [[0.1]], [{}])
        assert store.chroma_collection is not None

        store.delete_collection(COLLECTION_ID)
        assert store.chroma_collection is None


# ── get_collection_stats ─────────────────────────────────────────────────

class TestGetCollectionStats:
    """Tests for VectorStore.get_collection_stats."""

    def test_returns_stats_dict(self, store, chroma):
        """Stats include collection_id, total_vectors, and dimension."""
        mock_coll = MagicMock()
        mock_coll.count.return_value = 42
        chroma.get_collection.return_value = mock_coll

        stats = store.get_collection_stats(COLLECTION_ID)
        assert stats["collection_id"] == COLLECTION_ID
        assert stats["total_vectors"] == 42

    def test_missing_collection_returns_empty(self, store, chroma):
        """A missing collection returns an empty dict."""
        chroma.get_collection.side_effect = Exception("not found")
        assert store.get_collection_stats(COLLECTION_ID) == {}


# ── delete_document_vectors ──────────────────────────────────────────────

class TestDeleteDocumentVectors:
    """Tests for VectorStore.delete_document_vectors."""

    def test_deletes_by_document_id(self, store, chroma):
        """Vectors are deleted using a where filter on document_id."""
        mock_coll = MagicMock()
        chroma.get_collection.return_value = mock_coll

        store.delete_document_vectors(COLLECTION_ID, document_id=5, dimension=768)
        mock_coll.delete.assert_called_once_with(where={"document_id": 5})

    def test_missing_collection_no_error(self, store, chroma):
        """A missing collection does not raise."""
        chroma.get_collection.side_effect = Exception("nope")
        store.delete_document_vectors(COLLECTION_ID, document_id=1, dimension=768)
