"""Tests for DocumentProcessor: text extraction, semantic chunking, and the full pipeline.

All heavy dependencies (EmbeddingService, SemanticChunker, PdfReader) are mocked
so that these tests run without any ML models or real PDF files.
"""

import io
import pytest
from unittest.mock import patch, MagicMock

from werkzeug.datastructures import FileStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_storage(content: bytes = b"dummy", filename: str = "test.pdf",
                       content_type: str = "application/pdf") -> FileStorage:
    """Build a minimal FileStorage for tests."""
    return FileStorage(
        stream=io.BytesIO(content),
        filename=filename,
        content_type=content_type,
    )


def _build_processor(**kwargs):
    """Construct a DocumentProcessor with mocked ML dependencies."""
    with patch("app.services.document_processor.EmbeddingService") as mock_emb, \
         patch("app.services.document_processor.SemanticChunker") as mock_chunker:
        mock_emb.return_value.get_embedding_model.return_value = MagicMock()
        instance = mock_chunker.return_value
        instance.split_text.side_effect = lambda text: [text[:50]] if text else []
        from app.services.document_processor import DocumentProcessor
        processor = DocumentProcessor(**kwargs)
    return processor, instance


# ── chunk_document ────────────────────────────────────────────────────────

class TestChunkDocument:
    """Tests for DocumentProcessor.chunk_document."""

    def test_produces_chunks_from_pages(self):
        """Chunks are produced from multi-page input."""
        processor, _ = _build_processor()
        pages = [
            {"page_number": 1, "text": "First page content. " * 10},
            {"page_number": 2, "text": "Second page content. " * 10},
        ]
        chunks = processor.chunk_document(pages, "doc.pdf")
        assert len(chunks) >= 2
        for c in chunks:
            assert "content" in c
            assert "page_number" in c
            assert "chunk_index" in c
            assert c["metadata"]["source"] == "doc.pdf"

    def test_chunk_indices_are_sequential(self):
        """chunk_index values are 0..N-1 across all pages."""
        processor, _ = _build_processor()
        pages = [
            {"page_number": 1, "text": "Page one text."},
            {"page_number": 2, "text": "Page two text."},
        ]
        chunks = processor.chunk_document(pages, "doc.pdf")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_pages_returns_empty(self):
        """No chunks are produced when pages list is empty."""
        processor, _ = _build_processor()
        assert processor.chunk_document([], "empty.pdf") == []

    def test_metadata_contains_chunk_size(self):
        """Each chunk's metadata includes the character count."""
        processor, _ = _build_processor()
        pages = [{"page_number": 1, "text": "Some text here"}]
        chunks = processor.chunk_document(pages, "f.pdf")
        for c in chunks:
            assert c["metadata"]["chunk_size"] == len(c["content"])

    def test_page_number_propagated(self):
        """Each chunk carries the page_number from its source page."""
        processor, chunker = _build_processor()
        chunker.split_text.side_effect = lambda t: [t]
        pages = [
            {"page_number": 3, "text": "Page three."},
            {"page_number": 7, "text": "Page seven."},
        ]
        chunks = processor.chunk_document(pages, "x.pdf")
        assert chunks[0]["page_number"] == 3
        assert chunks[1]["page_number"] == 7


# ── extract_text_from_document ─────────────────────────────────────────────

class TestExtractTextFromDocument:
    """Tests for DocumentProcessor.extract_text_from_document."""

    @patch("app.services.document_processor.PdfReader")
    def test_pdf_extraction(self, mock_reader_cls):
        """PDF pages with text are extracted; blank pages are skipped."""
        processor, _ = _build_processor()

        mock_page_1 = MagicMock()
        mock_page_1.extract_text.return_value = "Hello World"
        mock_page_2 = MagicMock()
        mock_page_2.extract_text.return_value = "  "  # blank after strip
        mock_page_3 = MagicMock()
        mock_page_3.extract_text.return_value = "Page Three"
        mock_reader_cls.return_value.pages = [mock_page_1, mock_page_2, mock_page_3]

        fs = _make_file_storage(filename="sample.pdf")
        pages = processor.extract_text_from_document(fs, "sample.pdf")

        assert len(pages) == 2
        assert pages[0]["page_number"] == 1
        assert pages[0]["text"] == "Hello World"
        assert pages[1]["page_number"] == 3

    @patch("app.services.document_processor.PdfReader")
    def test_pdf_all_blank_pages(self, mock_reader_cls):
        """A PDF with only blank pages returns an empty list."""
        processor, _ = _build_processor()
        blank = MagicMock()
        blank.extract_text.return_value = ""
        mock_reader_cls.return_value.pages = [blank, blank]

        fs = _make_file_storage(filename="blank.pdf")
        pages = processor.extract_text_from_document(fs, "blank.pdf")
        assert pages == []

    def test_unsupported_extension_raises_value_error(self):
        """An unsupported file extension raises ValueError."""
        processor, _ = _build_processor()
        fs = _make_file_storage(filename="data.csv")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            processor.extract_text_from_document(fs, "data.csv")

    @patch("app.services.document_processor.PdfReader")
    def test_pdf_reader_exception_propagates(self, mock_reader_cls):
        """Exceptions from PdfReader bubble up."""
        processor, _ = _build_processor()
        mock_reader_cls.side_effect = RuntimeError("corrupt file")
        fs = _make_file_storage(filename="bad.pdf")
        with pytest.raises(RuntimeError, match="corrupt file"):
            processor.extract_text_from_document(fs, "bad.pdf")


# ── process_document (full pipeline) ─────────────────────────────────────

class TestProcessDocument:
    """Tests for DocumentProcessor.process_document."""

    @patch("app.services.document_processor.PdfReader")
    def test_returns_expected_structure(self, mock_reader_cls):
        """The result dict contains page_count, chunk_count, and chunks."""
        processor, _ = _build_processor()
        page = MagicMock()
        page.extract_text.return_value = "Some text for chunking."
        mock_reader_cls.return_value.pages = [page]

        fs = _make_file_storage(filename="doc.pdf")
        result = processor.process_document(fs, "doc.pdf")

        assert "page_count" in result
        assert "chunk_count" in result
        assert "chunks" in result
        assert result["page_count"] == 1
        assert result["chunk_count"] == len(result["chunks"])

    @patch("app.services.document_processor.PdfReader")
    def test_empty_pdf_returns_zero_counts(self, mock_reader_cls):
        """An empty PDF produces zero pages and zero chunks."""
        processor, _ = _build_processor()
        mock_reader_cls.return_value.pages = []

        fs = _make_file_storage(filename="empty.pdf")
        result = processor.process_document(fs, "empty.pdf")

        assert result["page_count"] == 0
        assert result["chunk_count"] == 0
        assert result["chunks"] == []
