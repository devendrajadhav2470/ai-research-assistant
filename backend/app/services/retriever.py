"""Hybrid retriever with vector search, BM25, Reciprocal Rank Fusion, and cross-encoder reranking."""

import logging
from typing import List, Dict, Any, Tuple

from sentence_transformers import CrossEncoder

from app.config import Config
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.bm25_index import BM25Index

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines FAISS vector search + BM25 keyword search with
    Reciprocal Rank Fusion (RRF) and cross-encoder reranking.
    """

    _reranker = None

    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
        bm25_index: BM25Index = None,
        top_k_retrieval: int = None,
        top_k_rerank: int = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.bm25_index = bm25_index or BM25Index()
        self.top_k_retrieval = top_k_retrieval or Config.TOP_K_RETRIEVAL
        self.top_k_rerank = top_k_rerank or Config.TOP_K_RERANK

    @classmethod
    def _get_reranker(cls) -> CrossEncoder:
        """Lazy-load the cross-encoder reranker model (singleton)."""
        if cls._reranker is None:
            logger.info(f"Loading reranker model: {Config.RERANKER_MODEL_NAME}")
            cls._reranker = CrossEncoder(Config.RERANKER_MODEL_NAME)
            logger.info("Reranker model loaded.")
        return cls._reranker

    def retrieve(
        self,
        collection_id: int,
        query: str,
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Full hybrid retrieval pipeline:
        1. FAISS vector search (top-K)
        2. BM25 keyword search (top-K)
        3. Reciprocal Rank Fusion to merge results
        4. Cross-encoder reranking on merged results
        5. Return top-N reranked results

        Args:
            collection_id: Collection to search in.
            query: User's natural language query.
            top_k: Final number of results to return.

        Returns:
            List of chunk dicts with scores and metadata.
        """
        top_k = top_k or self.top_k_rerank

        # Step 1: Vector search
        query_embedding = self.embedding_service.embed_query(query)
        vector_results = self.vector_store.search(
            collection_id=collection_id,
            query_embedding=query_embedding,
            top_k=self.top_k_retrieval,
            dimension=self.embedding_service.dimension,
        )

        # Step 2: BM25 keyword search
        bm25_results = self.bm25_index.search(
            collection_id=collection_id,
            query=query,
            top_k=self.top_k_retrieval,
        )

        # Step 3: Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(vector_results, bm25_results)

        if not fused_results:
            return []

        # Step 4: Cross-encoder reranking
        reranked = self._rerank(query, fused_results, top_k)

        logger.info(
            f"Hybrid retrieval for collection {collection_id}: "
            f"vector={len(vector_results)}, bm25={len(bm25_results)}, "
            f"fused={len(fused_results)}, reranked={len(reranked)}"
        )

        return reranked

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[Dict, float]],
        bm25_results: List[Tuple[Dict, float]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Merge results from multiple retrieval methods using RRF.

        RRF score = sum(1 / (k + rank_i)) for each method.

        Args:
            vector_results: Results from vector search.
            bm25_results: Results from BM25 search.
            k: RRF constant (default 60).

        Returns:
            Merged and scored list of chunk dicts.
        """
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # Process vector results
        for rank, (metadata, score) in enumerate(vector_results):
            key = self._chunk_key(metadata)
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in chunk_map:
                chunk_map[key] = {
                    **metadata,
                    "vector_score": score,
                    "vector_rank": rank + 1,
                }

        # Process BM25 results
        for rank, (metadata, score) in enumerate(bm25_results):
            key = self._chunk_key(metadata)
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in chunk_map:
                chunk_map[key] = {**metadata}
            chunk_map[key]["bm25_score"] = score
            chunk_map[key]["bm25_rank"] = rank + 1

        # Sort by RRF score
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for key in sorted_keys:
            chunk = chunk_map[key]
            chunk["rrf_score"] = rrf_scores[key]
            results.append(chunk)

        return results

    def _rerank(
        self, query: str, chunks: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks using a cross-encoder model.

        Args:
            query: The user query.
            chunks: List of chunk dicts to rerank.
            top_k: Number of top results to return.

        Returns:
            Top-k reranked chunks with rerank scores.
        """
        if not chunks:
            return []

        reranker = self._get_reranker()
        contents = [chunk.get("content", "") for chunk in chunks]

        # Create query-document pairs for the cross-encoder
        pairs = [[query, content] for content in contents]
        scores = reranker.predict(pairs)

        # Add rerank scores and sort
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return chunks[:top_k]

    @staticmethod
    def _chunk_key(metadata: Dict[str, Any]) -> str:
        """Create a unique key for a chunk based on its metadata."""
        doc_id = metadata.get("document_id", "")
        chunk_idx = metadata.get("chunk_index", "")
        return f"{doc_id}_{chunk_idx}"

