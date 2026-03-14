"""Document processing service: Document parsing and text chunking."""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any
from readability import Document as ReadabilityDocument  # pyright: ignore[reportMissingImports]
from docx import Document as DocxDocument
from pypdf import PdfReader
from langchain_experimental.text_splitter import SemanticChunker
from werkzeug.datastructures import FileStorage
from flask import current_app

from bs4 import BeautifulSoup
import io
from PIL import Image
import fitz  # PyMuPDF

from app.config import Config
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

    

class DocumentProcessor:
    """Handles Document parsing and text chunking with page-level metadata."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
        self.embeddings = embedding_service.get_embedding_model()

        self.chunker = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type="percentile",  # default
            breakpoint_threshold_amount=95,          # default for percentile
        )

    def extract_text_from_document(self, file: FileStorage, filename: str) -> List[Dict[str, Any]]:
        """
        Extract text from a file, page by page.

        Returns:
            List of dicts with 'page_number', 'text' keys.
        """
        # if not os.path.exists(file_path):
        #     raise FileNotFoundError(f"File not found: {file_path}")

        pages = []
        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".pdf":
                reader = PdfReader(file.stream)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    text = text.strip()
                    if text:
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                        })

                logger.info(
                    f"Extracted text from {len(pages)} pages of {filename}"
                )
            
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {file.filename}: {e}")
            raise

        return pages

    def chunk_document(
        self, pages: List[Dict[str, Any]], filename: str
    ) -> List[Dict[str, Any]]:
        """
        Split extracted pages into smaller chunks with metadata.

        Args:
            pages: List of page dicts from extract_text_from_document.
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
            page_chunks = self.chunker.split_text(text)

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

    def process_document(
        self, file: FileStorage, filename: str
    ) -> Dict[str, Any]:
        """
        Full pipeline: extract text from file and chunk it.

        Returns:
            Dict with 'page_count', 'chunk_count', 'chunks'.
        """
        pages = self.extract_text_from_document(file,filename)
        chunks = self.chunk_document(pages, filename)

        return {
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

