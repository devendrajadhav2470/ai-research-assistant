"""Embedding service using SentenceTransformers."""

import logging
from typing import List

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import Config
from flask import current_app

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings using a local SentenceTransformer model."""

    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        """Singleton to avoid loading the model multiple times."""
        logger.info(f"someone asked for a EmeddingService instance")
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info(f"EmbeddingService object created")
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._model is None:
            self.model_name = model_name or Config.EMBEDDING_MODEL_NAME
            logger.info(f"loading the HuggingFaceEmbeddings model: {self.model_name} with normalize_embeddings set to True")
            self._model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                encode_kwargs={"normalize_embeddings": True,"device": current_app.extensions["device"]}
            )
            if self._model:
                logger.info(f"successfully loaded the model")
            else:
                logger.info(f"there was some error loading the HuggingFace model")
            # temporarily hardcoded
            self.dimension = 768

    def get_embedding_model(self):
        return self._model
        
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), dimension).
        """
        if not texts:
            return np.array([])

        embeddings = self._model.embed_documents(
            texts
        )

        logger.info(f"embedding service has generated {len(embeddings)} embeddings each of length {len(embeddings[0])}")
        logger.info(f"first 5 values of the first embedding: {embeddings[0][:5]}")

        return np.array(embeddings).astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query string.

        Returns:
            numpy array of shape (dimension,).
        """
        embedding = self._model.embed_query(
            query
        )

        logger.info(f"embedding service has generated embedding for the query {str}")
        logger.info(f"first 5 values of the embedding: {embedding[:5]}")
        return np.array(embedding).astype(np.float32)

