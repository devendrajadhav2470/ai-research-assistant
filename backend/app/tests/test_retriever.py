"""Tests for the vector store and BM25 index."""

import os
import tempfile
import shutil
import unittest

import numpy as np

from app.services.vector_store import VectorStore
from app.services.bm25_index import BM25Index


class TestVectorStore(unittest.TestCase):
    """Test FAISS vector store operations."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = VectorStore(index_dir=self.temp_dir)
        self.dimension = 384
        self.collection_id = 1

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_search(self):
        """Test adding vectors and searching."""
        # Create test embeddings
        n_vectors = 10
        embeddings = np.random.randn(n_vectors, self.dimension).astype(np.float32)
        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        metadata = [
            {
                "document_id": 1,
                "chunk_index": i,
                "page_number": 1,
                "source": "test.pdf",
                "content": f"Test content {i}",
            }
            for i in range(n_vectors)
        ]

        self.store.add_vectors(
            self.collection_id, embeddings, metadata, self.dimension
        )

        # Search
        query = np.random.randn(self.dimension).astype(np.float32)
        query = query / np.linalg.norm(query)

        results = self.store.search(
            self.collection_id, query, top_k=5, dimension=self.dimension
        )

        self.assertLessEqual(len(results), 5)
        self.assertGreater(len(results), 0)

        # Results should be (metadata, score) tuples
        for metadata_item, score in results:
            self.assertIn("document_id", metadata_item)
            self.assertIsInstance(score, float)

    def test_persistence(self):
        """Test that indices persist to disk and can be reloaded."""
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        metadata = [
            {"document_id": 1, "chunk_index": i, "content": f"Content {i}"}
            for i in range(5)
        ]

        self.store.add_vectors(
            self.collection_id, embeddings, metadata, self.dimension
        )

        # Create new store instance (simulates restart)
        new_store = VectorStore(index_dir=self.temp_dir)

        query = np.random.randn(self.dimension).astype(np.float32)
        query = query / np.linalg.norm(query)

        results = new_store.search(
            self.collection_id, query, top_k=3, dimension=self.dimension
        )

        self.assertGreater(len(results), 0)

    def test_delete_document_vectors(self):
        """Test deleting vectors for a specific document."""
        # Add vectors for two documents
        for doc_id in [1, 2]:
            embeddings = np.random.randn(5, self.dimension).astype(np.float32)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            metadata = [
                {"document_id": doc_id, "chunk_index": i, "content": f"Doc{doc_id} chunk {i}"}
                for i in range(5)
            ]
            self.store.add_vectors(
                self.collection_id, embeddings, metadata, self.dimension
            )

        stats_before = self.store.get_collection_stats(self.collection_id, self.dimension)
        self.assertEqual(stats_before["total_vectors"], 10)

        # Delete document 1
        self.store.delete_document_vectors(
            self.collection_id, document_id=1, dimension=self.dimension
        )

        stats_after = self.store.get_collection_stats(self.collection_id, self.dimension)
        self.assertEqual(stats_after["total_vectors"], 5)

    def test_empty_search(self):
        """Test searching an empty index."""
        query = np.random.randn(self.dimension).astype(np.float32)
        results = self.store.search(
            self.collection_id, query, top_k=5, dimension=self.dimension
        )
        self.assertEqual(len(results), 0)


class TestBM25Index(unittest.TestCase):
    """Test BM25 keyword search index."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index = BM25Index(index_dir=self.temp_dir)
        self.collection_id = 1

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_search(self):
        """Test adding documents and searching."""
        texts = [
            "Machine learning is a subset of artificial intelligence",
            "Deep learning uses neural networks with many layers",
            "Natural language processing handles text data",
            "Computer vision deals with image recognition",
            "Reinforcement learning involves reward signals",
        ]
        metadata = [
            {"document_id": 1, "chunk_index": i, "content": t}
            for i, t in enumerate(texts)
        ]

        self.index.add_documents(self.collection_id, texts, metadata)

        results = self.index.search(
            self.collection_id, "neural networks deep learning", top_k=3
        )

        self.assertGreater(len(results), 0)
        # First result should be about deep learning/neural networks
        top_result = results[0]
        self.assertIn("neural networks", top_result[0]["content"].lower())

    def test_persistence(self):
        """Test BM25 index persistence."""
        texts = ["Test document about machine learning"]
        metadata = [{"document_id": 1, "chunk_index": 0, "content": texts[0]}]

        self.index.add_documents(self.collection_id, texts, metadata)

        # Create new instance
        new_index = BM25Index(index_dir=self.temp_dir)
        results = new_index.search(self.collection_id, "machine learning")

        self.assertGreater(len(results), 0)

    def test_delete_document(self):
        """Test removing a document from the index."""
        texts = ["First document content", "Second document content"]
        metadata = [
            {"document_id": 1, "chunk_index": 0, "content": texts[0]},
            {"document_id": 2, "chunk_index": 0, "content": texts[1]},
        ]

        self.index.add_documents(self.collection_id, texts, metadata)
        self.index.delete_document(self.collection_id, document_id=1)

        results = self.index.search(self.collection_id, "document content")

        # Should only find document 2
        for meta, score in results:
            self.assertNotEqual(meta["document_id"], 1)


if __name__ == "__main__":
    unittest.main()

