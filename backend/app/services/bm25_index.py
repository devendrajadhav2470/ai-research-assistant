"""BM25 keyword search index for hybrid retrieval."""

import os
import json
import pickle
import logging
from typing import List, Dict, Any, Tuple

import nltk
from rank_bm25 import BM25Okapi

from app.config import Config

logger = logging.getLogger(__name__)

# Ensure NLTK punkt tokenizer is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


def tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase and split into words."""
    return nltk.word_tokenize(text.lower())


class BM25Index:
    """Manages BM25 keyword indices per collection with disk persistence."""

    def __init__(self, index_dir: str = None):
        self.index_dir = index_dir or Config.FAISS_INDEX_DIR
        os.makedirs(self.index_dir, exist_ok=True)
        self._indices: Dict[int, BM25Okapi] = {}
        self._metadata: Dict[int, List[Dict[str, Any]]] = {}
        self._corpus: Dict[int, List[List[str]]] = {}

    def _index_path(self, collection_id: int) -> str:
        return os.path.join(self.index_dir, f"collection_{collection_id}_bm25.pkl")

    def _load_index(self, collection_id: int) -> None:
        """Load a BM25 index from disk."""
        index_path = self._index_path(collection_id)

        if os.path.exists(index_path):
            with open(index_path, "rb") as f:
                data = pickle.load(f)
                self._indices[collection_id] = data["index"]
                self._metadata[collection_id] = data["metadata"]
                self._corpus[collection_id] = data["corpus"]
            logger.info(
                f"Loaded BM25 index for collection {collection_id} "
                f"with {len(self._metadata[collection_id])} documents"
            )
        else:
            self._metadata[collection_id] = []
            self._corpus[collection_id] = []
            self._indices[collection_id] = None

    def _save_index(self, collection_id: int) -> None:
        """Persist BM25 index to disk."""
        index_path = self._index_path(collection_id)
        data = {
            "index": self._indices.get(collection_id),
            "metadata": self._metadata.get(collection_id, []),
            "corpus": self._corpus.get(collection_id, []),
        }
        with open(index_path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Saved BM25 index for collection {collection_id}")

    def add_documents(
        self,
        collection_id: int,
        texts: List[str],
        metadata_list: List[Dict[str, Any]],
    ) -> None:
        """
        Add documents to a collection's BM25 index.

        Args:
            collection_id: The collection to add to.
            texts: List of document texts.
            metadata_list: List of metadata dicts (one per text).
        """
        if collection_id not in self._corpus:
            self._load_index(collection_id)

        # Tokenize new documents
        new_tokens = [tokenize(text) for text in texts]

        self._corpus[collection_id].extend(new_tokens)
        self._metadata[collection_id].extend(metadata_list)

        # Rebuild BM25 index with full corpus
        if self._corpus[collection_id]:
            self._indices[collection_id] = BM25Okapi(self._corpus[collection_id])

        self._save_index(collection_id)
        logger.info(
            f"Added {len(texts)} documents to BM25 index for collection {collection_id}"
        )

    def search(
        self,
        collection_id: int,
        query: str,
        top_k: int = 20,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for relevant documents using BM25 scoring.

        Args:
            collection_id: The collection to search.
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of (metadata, score) tuples sorted by relevance.
        """
        if collection_id not in self._indices:
            self._load_index(collection_id)

        index = self._indices.get(collection_id)
        if index is None or not self._metadata.get(collection_id):
            return []

        query_tokens = tokenize(query)
        scores = index.get_scores(query_tokens)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    (self._metadata[collection_id][idx], float(scores[idx]))
                )

        return results

    def delete_collection(self, collection_id: int) -> None:
        """Remove a collection's BM25 index."""
        self._indices.pop(collection_id, None)
        self._metadata.pop(collection_id, None)
        self._corpus.pop(collection_id, None)

        index_path = self._index_path(collection_id)
        if os.path.exists(index_path):
            os.remove(index_path)
        logger.info(f"Deleted BM25 index for collection {collection_id}")

    def delete_document(self, collection_id: int, document_id: int) -> None:
        """Remove all entries for a specific document and rebuild index."""
        if collection_id not in self._corpus:
            self._load_index(collection_id)

        metadata = self._metadata.get(collection_id, [])
        corpus = self._corpus.get(collection_id, [])

        if not metadata:
            return

        # Filter out the document
        keep_indices = [
            i for i, m in enumerate(metadata) if m.get("document_id") != document_id
        ]

        self._metadata[collection_id] = [metadata[i] for i in keep_indices]
        self._corpus[collection_id] = [corpus[i] for i in keep_indices]

        # Rebuild BM25 index
        if self._corpus[collection_id]:
            self._indices[collection_id] = BM25Okapi(self._corpus[collection_id])
        else:
            self._indices[collection_id] = None

        self._save_index(collection_id)
        logger.info(
            f"Removed document {document_id} from BM25 index for collection {collection_id}"
        )

