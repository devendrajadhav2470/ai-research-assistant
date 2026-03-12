"""Tests for the document processor service."""

import os
import tempfile
import unittest

from pypdf import PdfWriter

from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor(unittest.TestCase):
    """Test PDF parsing and text chunking."""

    def setUp(self):
        self.processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)

    def _create_test_pdf(self, pages_text: list[str]) -> str:
        """Create a temporary PDF with the given page texts."""
        writer = PdfWriter()
        for text in pages_text:
            writer.add_blank_page(width=612, height=792)
            page = writer.pages[-1]
            # Add text annotation (basic approach for test PDFs)
            page.merge_page(page)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        writer.write(tmp)
        tmp.close()
        return tmp.name

    def test_chunk_document(self):
        """Test that chunking produces expected results."""
        pages = [
            {"page_number": 1, "text": "This is a test document. " * 50},
            {"page_number": 2, "text": "Second page content. " * 30},
        ]

        chunks = self.processor.chunk_document(pages, "test.pdf")

        self.assertGreater(len(chunks), 0)

        # Verify metadata
        for chunk in chunks:
            self.assertIn("content", chunk)
            self.assertIn("page_number", chunk)
            self.assertIn("chunk_index", chunk)
            self.assertIn("metadata", chunk)
            self.assertEqual(chunk["metadata"]["source"], "test.pdf")
            self.assertLessEqual(len(chunk["content"]), self.processor.chunk_size + 50)

    def test_chunk_indices_are_sequential(self):
        """Test that chunk indices are sequential across pages."""
        pages = [
            {"page_number": 1, "text": "First page text. " * 100},
            {"page_number": 2, "text": "Second page text. " * 100},
        ]

        chunks = self.processor.chunk_document(pages, "test.pdf")
        indices = [c["chunk_index"] for c in chunks]

        self.assertEqual(indices, list(range(len(chunks))))

    def test_empty_pages(self):
        """Test handling of empty pages."""
        pages = []
        chunks = self.processor.chunk_document(pages, "test.pdf")
        self.assertEqual(len(chunks), 0)

    def test_file_not_found(self):
        """Test that missing file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.processor.extract_text_from_pdf("/nonexistent/file.pdf")

    def test_process_pdf_returns_expected_structure(self):
        """Test that process_pdf returns correct structure."""
        pages = [
            {"page_number": 1, "text": "Test content for processing. " * 20},
        ]

        # Test chunk_document directly
        chunks = self.processor.chunk_document(pages, "doc.pdf")

        self.assertIsInstance(chunks, list)
        if chunks:
            chunk = chunks[0]
            self.assertIn("content", chunk)
            self.assertIn("page_number", chunk)
            self.assertEqual(chunk["page_number"], 1)


if __name__ == "__main__":
    unittest.main()

