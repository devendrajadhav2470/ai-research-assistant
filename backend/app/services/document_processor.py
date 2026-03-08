"""Document processing service: Document parsing and text chunking."""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any
from readability import Document as ReadabilityDocument  # pyright: ignore[reportMissingImports]
from docx import Document as DocxDocument
from pypdf import PdfReader
from langchain_experimental.text_splitter import SemanticChunker
from embedding_service import EmbeddingService

from bs4 import BeautifulSoup
import io
from PIL import Image
import pytesseract
import fitz  # PyMuPDF

from app.config import Config

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_EXE_PATH

def ocr_entire_page(pdf_path: str, page_number_0based: int) -> str:
    doc = fitz.open(pdf_path)
    page = doc[page_number_0based]

    # render: scale 3.0 ~ ~216 DPI if source  72dpi;is 4.0 is even better for small fonts
    mat = fitz.Matrix(4.0, 4.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.open(io.BytesIO(pix.tobytes("png")))

    # optional: basic preprocessing
    img = img.convert("L")
    img = img.point(lambda p: 255 if p > 180 else 0)  # simple threshold

    config = "--oem 1 --psm 6"  # try psm 4/6/11 depending on layout

    extracted_text = ""

    try:
        extracted_text = pytesseract.image_to_string(img, lang="eng", config=config)
    except Exception as e:
        logger.error(f"there was an error extracting text from pdf image using pytesseract: {e}")
    
    return extracted_text
    

class DocumentProcessor:
    """Handles Document parsing and text chunking with page-level metadata."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP

        embedding_service = EmbeddingService()
        self.embeddings = embedding_service.get_embedding_model()

        self.chunker = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type="percentile",  # default
            breakpoint_threshold_amount=95,          # default for percentile
        )

    def extract_text_from_document(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """
        Extract text from a file, page by page.

        Returns:
            List of dicts with 'page_number', 'text' keys.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        pages = []
        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".pdf":
                reader = PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    text = text.strip()
                    if text:
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                        })
                    else:
                        resources = page.get("/Resources")
                        
                        if not resources: 
                            continue                 
                               
                        # TO DO FIX: should not pass file_path here, this way 
                        # Every time i have to read the whole pdf from the disk
                        image_text = ocr_entire_page(file_path, i)
                            

                        if image_text.strip():
                            pages.append({
                                "page_number": i + 1,
                                "text": image_text.strip(),
                            })

                logger.info(
                    f"Extracted text from {len(pages)} pages of {filename}"
                )
            elif ext == ".docx":
                doc = DocxDocument(file_path)
                # We'll treat each paragraph as a "page" for simplicity here
                # TO DO: this is not working, the chunk is becoming too small (1-2 sentence) sometimes
                for i, para in enumerate(doc.paragraphs):
                    text = para.text or ""
                    if text.strip():
                        pages.append({
                            "page_number": i + 1,
                            "text": text.strip(),
                        })
                logger.info(
                    f"Extracted text from {len(pages)} paragraphs of {filename}"
                )
            
            elif (ext == ".txt" or ext == ".md"):
                with open(file_path,"r",encoding="utf-8") as f: 
                    text = f.read()
                
                if text.strip():
                    pages.append({
                        "page_number": 1,
                        "text": text.strip()
                    })

                logger.info(
                    f"Extracted text from {len(pages)} of {filename}"
                )
            elif (ext == ".html"):
                with open(file_path,"r",encoding="utf-8") as f:
                    html= f.read()
                doc = ReadabilityDocument(html)
                clean_html= doc.summary()
                soup = BeautifulSoup(clean_html,"html.parser")
                
                main_content = soup.find("main") or soup.find("article")
                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                else: 
                    # Remove unwanted elements
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()

                    # Get text
                    text = soup.get_text(separator="\n")

                    # Clean empty lines
                    lines = [line.strip() for line in text.splitlines()]
                    text = "\n".join(line for line in lines if line)

                if text.strip():
                    pages.append({
                        "page_number": 1,
                        "text": text.strip()
                    })

                logger.info(
                    f"Extracted text from {len(pages)} of {filename}"
                )
            
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
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
        self, file_path: str, filename: str
    ) -> Dict[str, Any]:
        """
        Full pipeline: extract text from file and chunk it.

        Returns:
            Dict with 'page_count', 'chunk_count', 'chunks'.
        """
        pages = self.extract_text_from_document(file_path,filename)
        chunks = self.chunk_document(pages, filename)

        return {
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

