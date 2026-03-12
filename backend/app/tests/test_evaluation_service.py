"""Tests for EvaluationService: LLM-as-Judge evaluation, response parsing, and formatting.

LLMService is fully mocked so no real LLM calls are made.
"""

import json
import pytest
from unittest.mock import MagicMock

from app.services.evaluation_service import EvaluationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """A MagicMock standing in for LLMService."""
    return MagicMock()


@pytest.fixture
def service(mock_llm):
    """EvaluationService wired to a mocked LLM."""
    return EvaluationService(llm_service=mock_llm)


VALID_EVAL_JSON = json.dumps({
    "faithfulness": {"score": 4, "explanation": "Well grounded"},
    "relevance": {"score": 5, "explanation": "Directly addresses question"},
    "completeness": {"score": 3, "explanation": "Missing some details"},
    "citation_accuracy": {"score": 4, "explanation": "Mostly correct"},
    "overall_score": 4.0,
    "summary": "Good quality answer",
})


# ── _parse_evaluation_response ────────────────────────────────────────────

class TestParseEvaluationResponse:
    """Tests for EvaluationService._parse_evaluation_response."""

    def test_valid_json(self, service):
        """Correctly parses a well-formed JSON evaluation response."""
        result = service._parse_evaluation_response(VALID_EVAL_JSON)
        assert result["faithfulness"]["score"] == 4
        assert result["overall_score"] == 4.0

    def test_markdown_wrapped_json(self, service):
        """Parses JSON wrapped in ```json ... ``` markdown fences."""
        wrapped = f"```json\n{VALID_EVAL_JSON}\n```"
        result = service._parse_evaluation_response(wrapped)
        assert result["overall_score"] == 4.0

    def test_invalid_json_returns_default(self, service):
        """Invalid JSON yields a default evaluation with score 0."""
        result = service._parse_evaluation_response("not valid json")
        assert result["overall_score"] == 0
        assert result.get("error") is True

    def test_missing_fields_are_filled(self, service):
        """Missing dimension fields are added with score 0."""
        partial = json.dumps({
            "faithfulness": {"score": 5, "explanation": "ok"},
            "overall_score": 5.0,
        })
        result = service._parse_evaluation_response(partial)
        assert result["relevance"]["score"] == 0
        assert result["completeness"]["score"] == 0
        assert result["citation_accuracy"]["score"] == 0

    def test_calculates_overall_when_missing(self, service):
        """If overall_score is absent, it's computed as the mean of dimensions."""
        data = {
            "faithfulness": {"score": 4, "explanation": "a"},
            "relevance": {"score": 4, "explanation": "b"},
            "completeness": {"score": 4, "explanation": "c"},
            "citation_accuracy": {"score": 4, "explanation": "d"},
        }
        result = service._parse_evaluation_response(json.dumps(data))
        assert result["overall_score"] == 4.0

    def test_whitespace_around_json(self, service):
        """Leading/trailing whitespace is tolerated."""
        result = service._parse_evaluation_response(f"  \n{VALID_EVAL_JSON}\n  ")
        assert result["overall_score"] == 4.0


# ── _default_evaluation ──────────────────────────────────────────────────

class TestDefaultEvaluation:
    """Tests for EvaluationService._default_evaluation."""

    def test_structure(self):
        """Default evaluation contains all required keys."""
        result = EvaluationService._default_evaluation("test error")
        assert result["overall_score"] == 0
        assert result["error"] is True
        assert "test error" in result["summary"]
        for dim in ("faithfulness", "relevance", "completeness", "citation_accuracy"):
            assert result[dim]["score"] == 0

    def test_empty_error_message(self):
        """Works with an empty error message."""
        result = EvaluationService._default_evaluation("")
        assert result["overall_score"] == 0


# ── _format_context ──────────────────────────────────────────────────────

class TestFormatContext:
    """Tests for EvaluationService._format_context."""

    def test_formats_chunks(self, service):
        """Chunks are formatted with source, page, and content."""
        chunks = [
            {"source": "a.pdf", "page_number": 1, "content": "Text A"},
            {"source": "b.pdf", "page_number": 5, "content": "Text B"},
        ]
        result = service._format_context(chunks)
        assert "a.pdf" in result
        assert "Page 1" in result
        assert "b.pdf" in result
        assert "Page 5" in result

    def test_empty_chunks_returns_no_context(self, service):
        """An empty list yields the 'No context provided.' sentinel."""
        assert service._format_context([]) == "No context provided."

    def test_missing_keys_use_defaults(self, service):
        """Chunks with missing keys use 'Unknown' and '?' defaults."""
        result = service._format_context([{"content": "text"}])
        assert "Unknown" in result
        assert "?" in result


# ── evaluate ─────────────────────────────────────────────────────────────

class TestEvaluate:
    """Tests for EvaluationService.evaluate (full evaluation flow)."""

    def test_successful_evaluation(self, service, mock_llm):
        """A successful LLM call returns a parsed evaluation dict."""
        mock_llm.generate.return_value = VALID_EVAL_JSON
        result = service.evaluate(
            question="What is ML?",
            answer="ML is machine learning.",
            context_chunks=[{"source": "d.pdf", "page_number": 1, "content": "ML info"}],
        )
        assert result["overall_score"] == 4.0
        mock_llm.generate.assert_called_once()

    def test_llm_exception_returns_default(self, service, mock_llm):
        """When the LLM raises, the default evaluation is returned."""
        mock_llm.generate.side_effect = RuntimeError("LLM down")
        result = service.evaluate(
            question="Q", answer="A", context_chunks=[],
        )
        assert result["overall_score"] == 0
        assert result["error"] is True

    def test_passes_provider_and_model(self, service, mock_llm):
        """provider and model_name are forwarded to LLMService.generate."""
        mock_llm.generate.return_value = VALID_EVAL_JSON
        service.evaluate(
            question="Q", answer="A", context_chunks=[],
            provider="anthropic", model_name="claude-sonnet-4-20250514",
        )
        call_kwargs = mock_llm.generate.call_args
        assert call_kwargs.kwargs["provider"] == "anthropic"
        assert call_kwargs.kwargs["model_name"] == "claude-sonnet-4-20250514"
