""" vector store with disk persistence."""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app

from app.config import Config
import numpy as np 

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages FAISS indices per collection with disk persistence."""

    def __init__(self, index_dir: str = None):

        self.chroma_client = current_app.extensions["chroma_client"]
        self.chroma_collection = None 

    def _get_collection_name(self, collection_id: int):
        #temporary method for backwards compatibility 
        return str(f"collection_{collection_id}")
    

    def _create_or_load_collection(self, collection_id: int, name: str="") -> None:
        """Create or load a chromadb collection."""
        try:
            self.chroma_collection = self.chroma_client.create_collection(
                name=self._get_collection_name(collection_id),
                get_or_create=True
            )
            logger.info(f"collection {self._get_collection_name(collection_id)} created in chromadb")
            logger.info(
                f"Loaded ChromDB collection {self._get_collection_name(collection_id)}"
            )
        except Exception as e:
            logger.error(f"Failed to create or get ChromaDB collection for collection {collection_id}: {e}")
            self.chroma_collection = None
    
    def _temp_transform(self, x: float):
        return 1/(np.exp(x)+1)

    def add_vectors(
        self,
        collection_id: int,
        chunk_ids: List[str],
        embeddings: List[str],
        metadata_list: List[Dict[str,any]]
    ) -> None:
        """
        Add vectors with metadata to a collection's index.

        Args:
            collection_id: The collection to add to.
            embeddings: numpy array of shape (n, dimension).
            metadata_list: List of metadata dicts (one per vector).
            dimension: Embedding dimension (needed for index creation).
        """
        if not self.chroma_collection:
            self._create_or_load_collection(collection_id)
        
        if self._get_collection_name(collection_id) != self.chroma_collection.name:
            self._create_or_load_collection(collection_id)
        
        if len(embeddings) == 0:
            return

        self.chroma_collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            metadatas =metadata_list
        )


        logger.info(
            f"Added {len(embeddings)} vectors to collection {collection_id}. "
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
        logger.info(f"trying to get collection {self._get_collection_name(collection_id)} from chromadb")
        try:
            collection = self.chroma_client.get_collection(name= self._get_collection_name(collection_id))
        except Exception as e:
            logger.error(f"there was an error getting collection {collection_id} from chroma db")
            return []

        query_results = collection.query(
            query_embeddings = [query_embedding],
            n_results = top_k
        )

        results = []
        for i in range(len(query_results['ids'][0])):
            distance = query_results['distances'][0][i]
            results.append((query_results['metadatas'][0][i], self._temp_transform(distance)))

        return results

    def delete_collection(self, collection_id: int) -> None:
        """Remove a collection from memory and disk."""

        try:
            self.chroma_client.delete_collection(self._get_collection_name(collection_id))
        except Exception as e: 
            logger.error(f"collection {collection_id} does not exist in db") 
            return 

        if(self.chroma_collection):
            if self.chroma_collection.name == self._get_collection_name(collection_id):
                self.chroma_collection = None

        logger.info(f"Deleted collection {collection_id}")

    def get_collection_stats(self, collection_id: int, dimension: int = 768) -> Dict[str, Any]:
        """Get statistics about a collection's index."""
        try:
            collection = self.chroma_client.get_collection(name= self._get_collection_name(collection_id))
        except Exception as e:
            logger.error(f"there was an error getting collection {collection_id} from chroma db")
            return {}
        

        return {
            "collection_id": collection_id,
            "total_vectors": collection.count(),
            "dimension": dimension,
        }
    
    def delete_document_vectors(self,collection_id: int,document_id: int, dimension: int) -> None:
        try:
            collection = self.chroma_client.get_collection(name= self._get_collection_name(collection_id))
        except Exception as e:
            logger.error(f"there was an error getting collection_{collection_id} from chroma db")
            return
        
        try: 
            collection.delete(
                where={
                    "document_id": document_id
                }
            )
        except Exception as e: 
            logger.error(f"there was an error deleting document vectors from vector store {e}")

        return


