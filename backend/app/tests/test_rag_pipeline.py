"""Tests for RAGPipeline: query orchestration, streaming, citation extraction, and context formatting.

All sub-services (HybridRetriever, LLMService, ChatService, EvaluationService)
are mocked so the pipeline logic is tested in isolation.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.rag_pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CHUNKS = [
    {
        "document_id": 1,
        "chunk_index": 0,
        "source": "paper.pdf",
        "page_number": 3,
        "content": "Machine learning is a subset of AI.",
        "rerank_score": 0.95,
    },
    {
        "document_id": 1,
        "chunk_index": 1,
        "source": "paper.pdf",
        "page_number": 4,
        "content": "Deep learning uses neural networks." * 10,
        "rerank_score": 0.82,
    },
    {
        "document_id": 2,
        "chunk_index": 0,
        "source": "guide.pdf",
        "page_number": 1,
        "content": "RAG combines retrieval with generation.",
        "rerank_score": 0.78,
    },
]


@pytest.fixture
def mock_deps():
    """Create mocked sub-services for RAGPipeline."""
    retriever = MagicMock()
    retriever.retrieve.return_value = SAMPLE_CHUNKS

    llm = MagicMock()
    llm.generate.return_value = "This is the answer."
    llm.generate_stream.return_value = iter(["This ", "is ", "the ", "answer."])

    chat = MagicMock()
    chat.get_chat_history.return_value = []

    evaluation = MagicMock()
    evaluation.evaluate.return_value = {"overall_score": 4.0}

    return retriever, llm, chat, evaluation


@pytest.fixture
def pipeline(mock_deps):
    """A RAGPipeline wired to mocked dependencies."""
    retriever, llm, chat, evaluation = mock_deps
    return RAGPipeline(
        retriever=retriever,
        llm_service=llm,
        chat_service=chat,
        evaluation_service=evaluation,
    )


# ── query (non-streaming) ────────────────────────────────────────────────

class TestQuery:
    """Tests for RAGPipeline.query."""

    def test_returns_expected_keys(self, pipeline):
        """Result dict contains answer, citations, chunks, model_info."""
        result = pipeline.query(collection_id=1, question="What is ML?")
        assert "answer" in result
        assert "citations" in result
        assert "chunks" in result
        assert "model_info" in result

    def test_answer_comes_from_llm(self, pipeline):
        """The answer field contains the LLM's generated text."""
        result = pipeline.query(collection_id=1, question="Q")
        assert result["answer"] == "This is the answer."

    def test_retriever_called_with_collection(self, pipeline, mock_deps):
        """The retriever is called with the correct collection_id."""
        pipeline.query(collection_id=42, question="Q")
        mock_deps[0].retrieve.assert_called_once()
        call_kwargs = mock_deps[0].retrieve.call_args.kwargs
        assert call_kwargs["collection_id"] == 42

    def test_model_info_uses_defaults(self, pipeline):
        """When provider/model_name are None, defaults appear in model_info."""
        result = pipeline.query(collection_id=1, question="Q")
        assert "provider" in result["model_info"]
        assert "model" in result["model_info"]


# ── query_stream ─────────────────────────────────────────────────────────

class TestQueryStream:
    """Tests for RAGPipeline.query_stream."""

    def test_yields_chunks_tokens_done(self, pipeline):
        """The stream yields chunks, token, and done events."""
        events = list(pipeline.query_stream(collection_id=1, question="Q"))
        types = [e["type"] for e in events]
        assert types[0] == "chunks"
        assert "token" in types
        assert types[-1] == "done"

    def test_done_event_contains_full_answer(self, pipeline):
        """The done event contains the concatenated answer."""
        events = list(pipeline.query_stream(collection_id=1, question="Q"))
        done = [e for e in events if e["type"] == "done"][0]
        assert done["data"]["answer"] == "This is the answer."

    def test_error_event_on_exception(self, mock_deps):
        """When the retriever raises, an error event is yielded."""
        retriever, llm, chat, evaluation = mock_deps
        retriever.retrieve.side_effect = RuntimeError("DB down")
        pipeline = RAGPipeline(
            retriever=retriever, llm_service=llm,
            chat_service=chat, evaluation_service=evaluation,
        )
        events = list(pipeline.query_stream(collection_id=1, question="Q"))
        assert any(e["type"] == "error" for e in events)


# ── evaluate_response ─────────────────────────────────────────────────────

class TestEvaluateResponse:
    """Tests for RAGPipeline.evaluate_response."""

    def test_delegates_to_evaluation_service(self, pipeline, mock_deps):
        """evaluate_response forwards to EvaluationService.evaluate."""
        result = pipeline.evaluate_response(
            question="Q", answer="A", chunks=SAMPLE_CHUNKS,
        )
        mock_deps[3].evaluate.assert_called_once()
        assert result["overall_score"] == 4.0


# ── _build_messages ──────────────────────────────────────────────────────

class TestBuildMessages:
    """Tests for RAGPipeline._build_messages."""

    def test_without_history(self, pipeline):
        """Without a conversation, messages are [system, user]."""
        msgs = pipeline._build_messages(question="Hello?", chunks=[])
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"

    def test_with_history(self, pipeline, mock_deps):
        """With chat history, history messages appear between system and user."""
        mock_deps[2].get_chat_history.return_value = [
            {"role": "user", "content": "prev Q"},
            {"role": "assistant", "content": "prev A"},
        ]
        msgs = pipeline._build_messages(
            question="new Q", chunks=[], conversation_id=1,
        )
        assert msgs[0]["role"] == "system"
        assert len(msgs) >= 3

    def test_deduplicates_user_question_from_history(self, pipeline, mock_deps):
        """If the user question is already the last history message, it is not duplicated."""
        mock_deps[2].get_chat_history.return_value = [
            {"role": "user", "content": "same Q"},
        ]
        msgs = pipeline._build_messages(
            question="same Q", chunks=[], conversation_id=1,
        )
        user_msgs = [m for m in msgs if m["role"] == "user"]
        assert len(user_msgs) == 1


# ── _format_context ──────────────────────────────────────────────────────

class TestFormatContext:
    """Tests for RAGPipeline._format_context."""

    def test_empty_chunks(self, pipeline):
        """Empty chunk list returns 'No relevant context found.'"""
        assert pipeline._format_context([]) == "No relevant context found."

    def test_formats_with_rerank_score(self, pipeline):
        """Chunks with rerank_score include relevance info."""
        result = pipeline._format_context(SAMPLE_CHUNKS[:1])
        assert "paper.pdf" in result
        assert "0.950" in result

    def test_ctx_tags_present(self, pipeline):
        """Output contains XML-like <ctx> tags."""
        result = pipeline._format_context(SAMPLE_CHUNKS[:1])
        assert "<ctx" in result
        assert "</ctx>" in result


# ── _extract_citations ───────────────────────────────────────────────────

class TestExtractCitations:
    """Tests for RAGPipeline._extract_citations."""

    def test_deduplication(self, pipeline):
        """Duplicate source+page combinations are deduplicated."""
        dup_chunks = [
            {"source": "a.pdf", "page_number": 1, "content": "x", "document_id": 1, "rerank_score": 0.9},
            {"source": "a.pdf", "page_number": 1, "content": "y", "document_id": 1, "rerank_score": 0.8},
        ]
        cites = pipeline._extract_citations(dup_chunks)
        assert len(cites) == 1

    def test_content_preview_truncation(self, pipeline):
        """Content previews longer than 200 chars are truncated with '...'."""
        long_content = "A" * 300
        chunks = [{"source": "x.pdf", "page_number": 1, "document_id": 1,
                    "content": long_content, "rerank_score": 0.5}]
        cites = pipeline._extract_citations(chunks)
        assert cites[0]["content_preview"].endswith("...")

    def test_short_content_not_truncated(self, pipeline):
        """Content within 200 chars does not end with '...'."""
        chunks = [{"source": "x.pdf", "page_number": 1, "document_id": 1,
                    "content": "short", "rerank_score": 0.5}]
        cites = pipeline._extract_citations(chunks)
        assert not cites[0]["content_preview"].endswith("...")

    def test_relevance_score_rounded(self, pipeline):
        """rerank_score is rounded to 3 decimal places."""
        chunks = [{"source": "x.pdf", "page_number": 1, "document_id": 1,
                    "content": "c", "rerank_score": 0.123456}]
        cites = pipeline._extract_citations(chunks)
        assert cites[0]["relevance_score"] == 0.123
