"""Document processing service: PDF parsing and recursive text chunking."""

import os
import logging
from typing import List, Dict, Any

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles PDF parsing and text chunking with page-level metadata."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from a PDF file, page by page.

        Returns:
            List of dicts with 'page_number', 'text' keys.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        pages = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({
                        "page_number": i + 1,
                        "text": text.strip(),
                    })
            logger.info(
                f"Extracted text from {len(pages)} pages of {os.path.basename(file_path)}"
            )
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise

        return pages

    def chunk_document(
        self, pages: List[Dict[str, Any]], filename: str
    ) -> List[Dict[str, Any]]:
        """
        Split extracted pages into smaller chunks with metadata.

        Args:
            pages: List of page dicts from extract_text_from_pdf.
            filename: Original filename for metadata.

        Returns:
            List of chunk dicts with 'content', 'page_number', 'chunk_index', 'metadata'.
        """
        chunks = []
        chunk_index = 0

        for page_data in pages:
            page_number = page_data["page_number"]
            text = page_data["text"]

            # Split page text into chunks
            page_chunks = self.text_splitter.split_text(text)

            for chunk_text in page_chunks:
                chunks.append({
                    "content": chunk_text,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "metadata": {
                        "source": filename,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                        "chunk_size": len(chunk_text),
                    },
                })
                chunk_index += 1

        logger.info(
            f"Created {len(chunks)} chunks from {len(pages)} pages of {filename}"
        )
        return chunks

    def process_pdf(
        self, file_path: str, filename: str
    ) -> Dict[str, Any]:
        """
        Full pipeline: extract text from PDF and chunk it.

        Returns:
            Dict with 'page_count', 'chunk_count', 'chunks'.
        """
        pages = self.extract_text_from_pdf(file_path)
        chunks = self.chunk_document(pages, filename)

        return {
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

