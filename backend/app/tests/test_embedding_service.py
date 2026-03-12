"""Tests for EmbeddingService: singleton behaviour, embedding generation.

HuggingFaceEmbeddings is fully mocked so no model is downloaded during tests.
"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from app.services.embedding_service import EmbeddingService


@pytest.fixture
def _mock_hf(app):
    """Patch HuggingFaceEmbeddings for all tests in this module."""
    with patch("app.services.embedding_service.HuggingFaceEmbeddings") as mock_cls:
        mock_model = MagicMock()
        mock_model.embed_documents.return_value = [
            [0.1] * 768, [0.2] * 768, [0.3] * 768,
        ]
        mock_model.embed_query.return_value = [0.5] * 768
        mock_cls.return_value = mock_model
        yield mock_cls


class TestEmbeddingServiceSingleton:
    """Verify singleton pattern on EmbeddingService."""

    def test_same_instance_returned(self, _mock_hf):
        """Two calls to EmbeddingService() return the same object."""
        a = EmbeddingService()
        b = EmbeddingService()
        assert a is b

    def test_fresh_instance_after_reset(self, _mock_hf):
        """After resetting class attributes, a new instance is created."""
        first = EmbeddingService()
        EmbeddingService._instance = None
        EmbeddingService._model = None
        second = EmbeddingService()
        assert first is not second


class TestEmbedTexts:
    """Tests for EmbeddingService.embed_texts."""

    def test_returns_numpy_array(self, _mock_hf):
        """embed_texts returns a float32 numpy array."""
        service = EmbeddingService()
        result = service.embed_texts(["hello", "world"])
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_empty_input_returns_empty_array(self, _mock_hf):
        """An empty list yields an empty numpy array."""
        service = EmbeddingService()
        result = service.embed_texts([])
        assert isinstance(result, np.ndarray)
        assert result.size == 0


class TestEmbedQuery:
    """Tests for EmbeddingService.embed_query."""

    def test_returns_1d_numpy_array(self, _mock_hf):
        """embed_query returns a 1-D float32 array."""
        service = EmbeddingService()
        result = service.embed_query("What is RAG?")
        assert isinstance(result, np.ndarray)
        assert result.ndim == 1
        assert result.dtype == np.float32


class TestGetEmbeddingModel:
    """Tests for EmbeddingService.get_embedding_model."""

    def test_returns_model_object(self, _mock_hf):
        """get_embedding_model returns the underlying HuggingFace model."""
        service = EmbeddingService()
        model = service.get_embedding_model()
        assert model is not None
