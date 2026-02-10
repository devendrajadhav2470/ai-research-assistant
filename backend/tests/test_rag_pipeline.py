"""Tests for RAG pipeline components."""

import unittest
from unittest.mock import MagicMock, patch

from app.services.evaluation_service import EvaluationService


class TestEvaluationService(unittest.TestCase):
    """Test the LLM-as-Judge evaluation service."""

    def setUp(self):
        self.mock_llm = MagicMock()
        self.service = EvaluationService(llm_service=self.mock_llm)

    def test_parse_valid_evaluation(self):
        """Test parsing a valid JSON evaluation response."""
        response = '''{
            "faithfulness": {"score": 4, "explanation": "Well grounded"},
            "relevance": {"score": 5, "explanation": "Directly addresses question"},
            "completeness": {"score": 3, "explanation": "Missing some details"},
            "citation_accuracy": {"score": 4, "explanation": "Mostly correct"},
            "overall_score": 4.0,
            "summary": "Good quality answer"
        }'''

        result = self.service._parse_evaluation_response(response)

        self.assertEqual(result["faithfulness"]["score"], 4)
        self.assertEqual(result["relevance"]["score"], 5)
        self.assertEqual(result["completeness"]["score"], 3)
        self.assertEqual(result["citation_accuracy"]["score"], 4)
        self.assertEqual(result["overall_score"], 4.0)

    def test_parse_markdown_wrapped_json(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = '''```json
{
    "faithfulness": {"score": 5, "explanation": "All claims supported"},
    "relevance": {"score": 4, "explanation": "Relevant"},
    "completeness": {"score": 4, "explanation": "Comprehensive"},
    "citation_accuracy": {"score": 5, "explanation": "Accurate citations"},
    "overall_score": 4.5,
    "summary": "High quality"
}
```'''

        result = self.service._parse_evaluation_response(response)
        self.assertEqual(result["overall_score"], 4.5)

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON response."""
        response = "This is not valid JSON at all"
        result = self.service._parse_evaluation_response(response)
        self.assertTrue(result.get("error", False) or result["overall_score"] == 0)

    def test_default_evaluation(self):
        """Test the default evaluation fallback."""
        result = EvaluationService._default_evaluation("test error")
        self.assertEqual(result["overall_score"], 0)
        self.assertTrue(result["error"])
        self.assertIn("test error", result["summary"])

    def test_format_context(self):
        """Test formatting of context chunks."""
        chunks = [
            {"source": "paper.pdf", "page_number": 1, "content": "Test content"},
            {"source": "doc.pdf", "page_number": 5, "content": "More content"},
        ]

        result = self.service._format_context(chunks)
        self.assertIn("paper.pdf", result)
        self.assertIn("Page 1", result)
        self.assertIn("doc.pdf", result)
        self.assertIn("Page 5", result)

    def test_format_empty_context(self):
        """Test formatting with no context."""
        result = self.service._format_context([])
        self.assertEqual(result, "No context provided.")

    def test_evaluate_calls_llm(self):
        """Test that evaluate calls the LLM service."""
        self.mock_llm.generate.return_value = '''{
            "faithfulness": {"score": 4, "explanation": "Good"},
            "relevance": {"score": 4, "explanation": "Good"},
            "completeness": {"score": 4, "explanation": "Good"},
            "citation_accuracy": {"score": 4, "explanation": "Good"},
            "overall_score": 4.0,
            "summary": "Good answer"
        }'''

        result = self.service.evaluate(
            question="What is ML?",
            answer="ML is machine learning.",
            context_chunks=[{"source": "doc.pdf", "page_number": 1, "content": "ML is machine learning."}],
        )

        self.mock_llm.generate.assert_called_once()
        self.assertEqual(result["overall_score"], 4.0)


class TestRRF(unittest.TestCase):
    """Test Reciprocal Rank Fusion logic."""

    def test_rrf_merges_results(self):
        """Test that RRF correctly merges results from two sources."""
        from app.services.retriever import HybridRetriever

        retriever = HybridRetriever.__new__(HybridRetriever)

        vector_results = [
            ({"document_id": 1, "chunk_index": 0, "content": "A"}, 0.9),
            ({"document_id": 1, "chunk_index": 1, "content": "B"}, 0.8),
            ({"document_id": 2, "chunk_index": 0, "content": "C"}, 0.7),
        ]
        bm25_results = [
            ({"document_id": 2, "chunk_index": 0, "content": "C"}, 5.0),
            ({"document_id": 1, "chunk_index": 0, "content": "A"}, 3.0),
            ({"document_id": 3, "chunk_index": 0, "content": "D"}, 2.0),
        ]

        fused = retriever._reciprocal_rank_fusion(vector_results, bm25_results)

        self.assertGreater(len(fused), 0)
        # All unique chunks should be present
        chunk_keys = {f"{r['document_id']}_{r['chunk_index']}" for r in fused}
        self.assertIn("1_0", chunk_keys)
        self.assertIn("1_1", chunk_keys)
        self.assertIn("2_0", chunk_keys)
        self.assertIn("3_0", chunk_keys)

        # RRF scores should be present
        for result in fused:
            self.assertIn("rrf_score", result)
            self.assertGreater(result["rrf_score"], 0)

    def test_rrf_empty_inputs(self):
        """Test RRF with empty inputs."""
        from app.services.retriever import HybridRetriever

        retriever = HybridRetriever.__new__(HybridRetriever)
        fused = retriever._reciprocal_rank_fusion([], [])
        self.assertEqual(len(fused), 0)


if __name__ == "__main__":
    unittest.main()

