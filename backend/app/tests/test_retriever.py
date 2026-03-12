"""Tests for HybridRetriever: retrieve pipeline, RRF fusion, cross-encoder reranking.

All external dependencies (EmbeddingService, VectorStore, BM25Index, CrossEncoder)
are mocked.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.services.retriever import HybridRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VECTOR_RESULTS = [
    ({"document_id": 1, "chunk_index": 0, "content": "Chunk A"}, 0.9),
    ({"document_id": 1, "chunk_index": 1, "content": "Chunk B"}, 0.8),
    ({"document_id": 2, "chunk_index": 0, "content": "Chunk C"}, 0.7),
]

BM25_RESULTS = [
    ({"document_id": 2, "chunk_index": 0, "content": "Chunk C"}, 5.0),
    ({"document_id": 1, "chunk_index": 0, "content": "Chunk A"}, 3.0),
    ({"document_id": 3, "chunk_index": 0, "content": "Chunk D"}, 2.0),
]


@pytest.fixture
def mock_services(app):
    """Mocked embedding, vector, and BM25 services."""
    embedding = MagicMock()
    embedding.embed_query.return_value = np.random.randn(768).astype(np.float32)
    embedding.dimension = 768

    vector = MagicMock()
    vector.search.return_value = list(VECTOR_RESULTS)

    bm25 = MagicMock()
    bm25.search.return_value = list(BM25_RESULTS)

    return embedding, vector, bm25


@pytest.fixture
def retriever(mock_services):
    """HybridRetriever wired to mocked sub-services."""
    embedding, vector, bm25 = mock_services
    return HybridRetriever(
        embedding_service=embedding,
        vector_store=vector,
        bm25_index=bm25,
        top_k_retrieval=20,
        top_k_rerank=3,
    )


# ── _chunk_key ───────────────────────────────────────────────────────────

class TestChunkKey:
    """Tests for HybridRetriever._chunk_key."""

    def test_key_format(self):
        """Key is '{document_id}_{chunk_index}'."""
        key = HybridRetriever._chunk_key({"document_id": 5, "chunk_index": 2})
        assert key == "5_2"

    def test_missing_fields_use_empty(self):
        """Missing keys default to empty string."""
        key = HybridRetriever._chunk_key({})
        assert key == "_"


# ── _reciprocal_rank_fusion ──────────────────────────────────────────────

class TestReciprocalRankFusion:
    """Tests for HybridRetriever._reciprocal_rank_fusion."""

    def test_merges_results(self, retriever):
        """All unique chunks from both sources appear in fused results."""
        fused = retriever._reciprocal_rank_fusion(VECTOR_RESULTS, BM25_RESULTS)
        keys = {f"{r['document_id']}_{r['chunk_index']}" for r in fused}
        assert "1_0" in keys
        assert "1_1" in keys
        assert "2_0" in keys
        assert "3_0" in keys

    def test_rrf_scores_present(self, retriever):
        """Every fused result has a positive rrf_score."""
        fused = retriever._reciprocal_rank_fusion(VECTOR_RESULTS, BM25_RESULTS)
        for r in fused:
            assert "rrf_score" in r
            assert r["rrf_score"] > 0

    def test_overlap_boosts_score(self, retriever):
        """Chunks appearing in both sources have higher RRF scores."""
        fused = retriever._reciprocal_rank_fusion(VECTOR_RESULTS, BM25_RESULTS)
        scores = {f"{r['document_id']}_{r['chunk_index']}": r["rrf_score"]
                  for r in fused}
        # 1_0 and 2_0 appear in both; 1_1 and 3_0 only in one
        assert scores["1_0"] > scores["1_1"]
        assert scores["2_0"] > scores["3_0"]

    def test_empty_inputs(self, retriever):
        """Empty input lists produce an empty result."""
        assert retriever._reciprocal_rank_fusion([], []) == []

    def test_one_source_empty(self, retriever):
        """When one source is empty, the other's results still appear."""
        fused = retriever._reciprocal_rank_fusion(VECTOR_RESULTS, [])
        assert len(fused) == len(VECTOR_RESULTS)


# ── _rerank ──────────────────────────────────────────────────────────────

class TestRerank:
    """Tests for HybridRetriever._rerank."""

    @patch.object(HybridRetriever, "_get_reranker")
    def test_reranks_and_truncates(self, mock_get_reranker, retriever):
        """Reranking sorts by cross-encoder score and returns top_k."""
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [0.1, 0.9, 0.5]
        mock_get_reranker.return_value = mock_reranker

        chunks = [
            {"content": "low"}, {"content": "high"}, {"content": "mid"},
        ]
        result = retriever._rerank("query", chunks, top_k=2)
        assert len(result) == 2
        assert result[0]["rerank_score"] == 0.9

    @patch.object(HybridRetriever, "_get_reranker")
    def test_empty_chunks(self, mock_get_reranker, retriever):
        """Empty chunk list returns empty without calling the reranker."""
        assert retriever._rerank("q", [], top_k=5) == []
        mock_get_reranker.assert_not_called()


# ── retrieve (full pipeline) ─────────────────────────────────────────────

class TestRetrieve:
    """Tests for HybridRetriever.retrieve (end-to-end)."""

    @patch.object(HybridRetriever, "_get_reranker")
    def test_full_pipeline(self, mock_get_reranker, retriever, mock_services):
        """The full retrieve pipeline returns reranked results."""
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [0.8, 0.6, 0.9, 0.3]
        mock_get_reranker.return_value = mock_reranker

        results = retriever.retrieve(collection_id=1, query="test query")
        assert len(results) <= retriever.top_k_rerank
        mock_services[0].embed_query.assert_called_once_with("test query")
        mock_services[1].search.assert_called_once()
        mock_services[2].search.assert_called_once()

    @patch.object(HybridRetriever, "_get_reranker")
    def test_returns_empty_when_no_results(self, mock_get_reranker, mock_services, app):
        """If both sources return nothing, an empty list is returned."""
        embedding, vector, bm25 = mock_services
        vector.search.return_value = []
        bm25.search.return_value = []
        r = HybridRetriever(
            embedding_service=embedding, vector_store=vector, bm25_index=bm25,
        )
        assert r.retrieve(collection_id=1, query="q") == []
