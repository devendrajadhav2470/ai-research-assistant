"""FAISS vector store with disk persistence."""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple

import faiss
import numpy as np

from app.config import Config

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages FAISS indices per collection with disk persistence."""

    def __init__(self, index_dir: str = None):
        self.index_dir = index_dir or Config.FAISS_INDEX_DIR
        os.makedirs(self.index_dir, exist_ok=True)
        self._indices: Dict[int, faiss.Index] = {}
        self._metadata: Dict[int, List[Dict[str, Any]]] = {}

    def _index_path(self, collection_id: int) -> str:
        return os.path.join(self.index_dir, f"collection_{collection_id}.faiss")

    def _metadata_path(self, collection_id: int) -> str:
        return os.path.join(self.index_dir, f"collection_{collection_id}_meta.json")

    def _load_index(self, collection_id: int, dimension: int) -> None:
        """Load or create a FAISS index for a collection."""
        index_path = self._index_path(collection_id)
        meta_path = self._metadata_path(collection_id)

        if os.path.exists(index_path) and os.path.exists(meta_path):
            # Use Python file I/O + deserialize_index to avoid
            # faiss.read_index() failing on Windows ([Errno 22])
            with open(index_path, "rb") as f:
                index_data = np.frombuffer(f.read(), dtype=np.uint8)
            self._indices[collection_id] = faiss.deserialize_index(index_data)
            with open(meta_path, "r") as f:
                self._metadata[collection_id] = json.load(f)
            logger.info(
                f"Loaded FAISS index for collection {collection_id} "
                f"with {self._indices[collection_id].ntotal} vectors"
            )
        else:
            # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
            self._indices[collection_id] = faiss.IndexFlatIP(dimension)
            self._metadata[collection_id] = []
            logger.info(
                f"Created new FAISS index for collection {collection_id} "
                f"with dimension {dimension}"
            )

    def _save_index(self, collection_id: int) -> None:
        """Persist FAISS index and metadata to disk."""
        if collection_id in self._indices:
            # Use Python file I/O + serialize_index to avoid
            # faiss.write_index() failing on Windows ([Errno 22])
            index_data = faiss.serialize_index(self._indices[collection_id])
            with open(self._index_path(collection_id), "wb") as f:
                f.write(index_data.tobytes())
            with open(self._metadata_path(collection_id), "w") as f:
                json.dump(self._metadata[collection_id], f)
            logger.info(f"Saved FAISS index for collection {collection_id}")

    def add_vectors(
        self,
        collection_id: int,
        embeddings: np.ndarray,
        metadata_list: List[Dict[str, Any]],
        dimension: int,
    ) -> None:
        """
        Add vectors with metadata to a collection's index.

        Args:
            collection_id: The collection to add to.
            embeddings: numpy array of shape (n, dimension).
            metadata_list: List of metadata dicts (one per vector).
            dimension: Embedding dimension (needed for index creation).
        """
        if collection_id not in self._indices:
            self._load_index(collection_id, dimension)

        if len(embeddings) == 0:
            return

        self._indices[collection_id].add(embeddings)
        self._metadata[collection_id].extend(metadata_list)
        self._save_index(collection_id)

        logger.info(
            f"Added {len(embeddings)} vectors to collection {collection_id}. "
            f"Total: {self._indices[collection_id].ntotal}"
        )

    def search(
        self,
        collection_id: int,
        query_embedding: np.ndarray,
        top_k: int = 20,
        dimension: int = 384,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_id: The collection to search.
            query_embedding: Query vector of shape (dimension,).
            top_k: Number of results to return.
            dimension: Embedding dimension.

        Returns:
            List of (metadata, score) tuples sorted by similarity.
        """
        if collection_id not in self._indices:
            self._load_index(collection_id, dimension)

        index = self._indices.get(collection_id)
        if index is None or index.ntotal == 0:
            return []

        # Reshape query for FAISS
        query = query_embedding.reshape(1, -1).astype(np.float32)
        actual_k = min(top_k, index.ntotal)

        scores, indices = index.search(query, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._metadata[collection_id]):
                results.append((self._metadata[collection_id][idx], float(score)))

        return results

    def delete_collection(self, collection_id: int) -> None:
        """Remove a collection's index from memory and disk."""
        # Remove from memory
        self._indices.pop(collection_id, None)
        self._metadata.pop(collection_id, None)

        # Remove from disk
        index_path = self._index_path(collection_id)
        meta_path = self._metadata_path(collection_id)
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

        logger.info(f"Deleted FAISS index for collection {collection_id}")

    def delete_document_vectors(
        self, collection_id: int, document_id: int, dimension: int = 384
    ) -> None:
        """
        Remove all vectors for a specific document from a collection.
        Rebuilds the index since FAISS doesn't support deletion natively.
        """
        if collection_id not in self._indices:
            self._load_index(collection_id, dimension)

        metadata = self._metadata.get(collection_id, [])
        if not metadata:
            return

        # Find indices to keep
        keep_indices = [
            i for i, m in enumerate(metadata) if m.get("document_id") != document_id
        ]

        if len(keep_indices) == len(metadata):
            return  # Nothing to delete

        if not keep_indices:
            # All vectors belong to this document, clear everything
            self._indices[collection_id] = faiss.IndexFlatIP(dimension)
            self._metadata[collection_id] = []
        else:
            # Reconstruct vectors for items to keep
            old_index = self._indices[collection_id]
            vectors = np.array(
                [old_index.reconstruct(i) for i in keep_indices]
            ).astype(np.float32)

            new_index = faiss.IndexFlatIP(dimension)
            new_index.add(vectors)
            self._indices[collection_id] = new_index
            self._metadata[collection_id] = [metadata[i] for i in keep_indices]

        self._save_index(collection_id)
        logger.info(
            f"Removed vectors for document {document_id} from collection {collection_id}"
        )

    def get_collection_stats(self, collection_id: int, dimension: int = 384) -> Dict[str, Any]:
        """Get statistics about a collection's index."""
        if collection_id not in self._indices:
            self._load_index(collection_id, dimension)

        index = self._indices.get(collection_id)
        return {
            "collection_id": collection_id,
            "total_vectors": index.ntotal if index else 0,
            "dimension": index.d if index else dimension,
        }

