"""Tests for BM25Index: singleton behaviour, index management, search, and deletion.

Database interactions (Chunk.query, db.session.get) are mocked since the index
operates on tokens stored in the database.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.bm25_index import BM25Index, tokenize


# ---------------------------------------------------------------------------
# tokenize helper
# ---------------------------------------------------------------------------

class TestTokenize:
    """Tests for the module-level tokenize function."""

    @patch("app.services.bm25_index.nltk.word_tokenize")
    def test_lowercases_and_tokenises(self, mock_tok):
        """Input is lowered before tokenising."""
        mock_tok.return_value = ["hello", "world"]
        result = tokenize("Hello World")
        mock_tok.assert_called_once_with("hello world")
        assert result == ["hello", "world"]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestBM25Singleton:
    """Verify the singleton pattern on BM25Index."""

    def test_same_instance(self, app):
        """Two instantiations return the same object."""
        a = BM25Index()
        b = BM25Index()
        assert a is b

    def test_fresh_after_reset(self, app):
        """Resetting _instance produces a new object."""
        first = BM25Index()
        BM25Index._instance = None
        second = BM25Index()
        assert first is not second


# ---------------------------------------------------------------------------
# _load_index
# ---------------------------------------------------------------------------

class TestLoadIndex:
    """Tests for BM25Index._load_index."""

    @patch("app.services.bm25_index.Chunk")
    def test_loads_from_db(self, mock_chunk_model, app):
        """Chunks are fetched from DB and an Okapi BM25 index is built."""
        mock_c1 = MagicMock()
        mock_c1.metadata_json = '{"source": "a.pdf"}'
        mock_c1.chunk_tokens = ["hello", "world"]
        mock_c2 = MagicMock()
        mock_c2.metadata_json = '{"source": "b.pdf"}'
        mock_c2.chunk_tokens = ["foo", "bar"]
        mock_chunk_model.query.filter_by.return_value.all.return_value = [mock_c1, mock_c2]

        idx = BM25Index()
        idx._load_index(1)

        assert 1 in idx._metadata
        assert len(idx._metadata[1]) == 2
        assert idx._indices[1] is not None

    @patch("app.services.bm25_index.Chunk")
    def test_empty_collection(self, mock_chunk_model, app):
        """An empty collection yields empty internal structures."""
        mock_chunk_model.query.filter_by.return_value.all.return_value = []

        idx = BM25Index()
        idx._load_index(99)

        assert idx._metadata.get(99) == []
        assert idx._indices.get(99) is None


# ---------------------------------------------------------------------------
# add_documents
# ---------------------------------------------------------------------------

class TestAddDocuments:
    """Tests for BM25Index.add_documents."""

    @patch("app.services.bm25_index.Chunk")
    @patch("app.services.bm25_index.db")
    def test_loads_index_when_collection_exists(self, mock_db, mock_chunk, app):
        """add_documents triggers _load_index for a valid collection."""
        mock_collection = MagicMock()
        mock_db.session.get.return_value = mock_collection
        mock_chunk.query.filter_by.return_value.all.return_value = []

        idx = BM25Index()
        idx.add_documents(collection_id=1)
        mock_db.session.get.assert_called_once()

    @patch("app.services.bm25_index.db")
    def test_skips_when_collection_missing(self, mock_db, app):
        """add_documents returns early when the collection doesn't exist."""
        mock_db.session.get.return_value = None
        idx = BM25Index()
        idx.add_documents(collection_id=999)
        # _load_index should NOT be called, so _indices stays empty
        assert 999 not in idx._indices


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    """Tests for BM25Index.search."""

    @patch("app.services.bm25_index.Chunk")
    @patch("app.services.bm25_index.db")
    @patch("app.services.bm25_index.tokenize")
    def test_returns_results(self, mock_tok, mock_db, mock_chunk, app):
        """search returns (metadata, score) tuples for matching documents."""
        mock_db.session.get.return_value = MagicMock()  # collection exists

        mock_c = MagicMock()
        mock_c.metadata_json = '{"source": "doc.pdf", "content": "machine learning text"}'
        mock_c.chunk_tokens = ["machine", "learning", "text"]
        mock_chunk.query.filter_by.return_value.all.return_value = [mock_c]

        mock_tok.return_value = ["machine", "learning"]

        idx = BM25Index()
        idx._load_index(1)
        results = idx.search(collection_id=1, query="machine learning", top_k=5)

        assert len(results) >= 1
        meta, score = results[0]
        assert score > 0

    @patch("app.services.bm25_index.db")
    def test_missing_collection_returns_empty(self, mock_db, app):
        """search returns [] when the collection doesn't exist in DB."""
        mock_db.session.get.return_value = None
        idx = BM25Index()
        assert idx.search(collection_id=999, query="anything") == []

    @patch("app.services.bm25_index.Chunk")
    @patch("app.services.bm25_index.db")
    def test_empty_index_returns_empty(self, mock_db, mock_chunk, app):
        """search returns [] when the BM25 index is None (no documents)."""
        mock_db.session.get.return_value = MagicMock()
        mock_chunk.query.filter_by.return_value.all.return_value = []

        idx = BM25Index()
        idx._load_index(1)
        assert idx.search(collection_id=1, query="anything") == []


# ---------------------------------------------------------------------------
# delete_collection
# ---------------------------------------------------------------------------

class TestDeleteCollection:
    """Tests for BM25Index.delete_collection."""

    def test_removes_internal_state(self, app):
        """Internal dicts are cleaned up."""
        idx = BM25Index()
        idx._indices[5] = MagicMock()
        idx._metadata[5] = [{"a": 1}]
        idx._corpus[5] = [["token"]]

        idx.delete_collection(5)
        assert 5 not in idx._indices
        assert 5 not in idx._metadata
        assert 5 not in idx._corpus

    def test_no_error_when_absent(self, app):
        """Deleting a non-existent collection does not raise."""
        idx = BM25Index()
        idx.delete_collection(9999)


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    """Tests for BM25Index.delete_document."""

    @patch("app.services.bm25_index.Chunk")
    def test_filters_and_rebuilds(self, mock_chunk, app):
        """After deleting a document, only the remaining docs are in the index."""
        mock_c1 = MagicMock()
        mock_c1.metadata_json = '{"document_id": 1}'
        mock_c1.chunk_tokens = ["alpha"]
        mock_c2 = MagicMock()
        mock_c2.metadata_json = '{"document_id": 2}'
        mock_c2.chunk_tokens = ["beta"]
        mock_chunk.query.filter_by.return_value.all.return_value = [mock_c1, mock_c2]

        idx = BM25Index()
        idx._load_index(1)
        assert len(idx._metadata[1]) == 2

        idx.delete_document(collection_id=1, document_id=1)
        assert len(idx._metadata[1]) == 1
        assert idx._metadata[1][0]["document_id"] == 2

    def test_no_error_when_corpus_empty(self, app):
        """Deleting from an empty corpus does not raise."""
        idx = BM25Index()
        idx._metadata[1] = []
        idx._corpus[1] = []
        idx.delete_document(collection_id=1, document_id=1)
