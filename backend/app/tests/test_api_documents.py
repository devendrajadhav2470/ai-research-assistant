"""Tests for the documents API blueprint: list, upload, get, delete.

Heavy processing (DocumentProcessor, EmbeddingService, VectorStore, BM25Index,
S3) is fully mocked.
"""

import io
import json
import pytest
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models.document import Document
from app.tests.conftest import SAMPLE_USER_PAYLOAD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed headers."""
    return auth_headers


def _pdf_file(name: str = "test.pdf", size: int = 128) -> tuple:
    """Build a (BytesIO, filename) pair mimicking a PDF upload."""
    return (io.BytesIO(b"%PDF-" + b"x" * size), name)


# ── GET /api/documents/collection/<id> ────────────────────────────────────

class TestListDocuments:
    """Tests for GET /api/documents/collection/<collection_id>."""

    def test_returns_documents(self, client, headers, sample_document):
        """Returns a list of documents for a valid collection."""
        cid = sample_document.collection_id
        resp = client.get(f"/api/documents/collection/{cid}", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]["filename"] == "test.pdf"

    def test_collection_not_found(self, client, headers):
        """Returns 404 when the collection does not exist."""
        resp = client.get("/api/documents/collection/99999", headers=headers)
        assert resp.status_code == 404


# ── POST /api/documents/upload/<id> ──────────────────────────────────────

class TestUploadDocument:
    """Tests for POST /api/documents/upload/<collection_id>."""

    @patch("app.api.documents.BM25Index")
    @patch("app.api.documents.VectorStore")
    @patch("app.api.documents.EmbeddingService")
    @patch("app.api.documents.DocumentProcessor")
    @patch("app.api.documents.upload_file_to_s3")
    def test_successful_upload(
        self, mock_s3, mock_proc_cls, mock_emb_cls, mock_vs_cls,
        mock_bm25_cls, client, headers, sample_collection,
    ):
        """A valid PDF upload returns 201 with the document dict."""
        mock_proc = mock_proc_cls.return_value
        mock_proc.process_document.return_value = {
            "page_count": 2,
            "chunk_count": 3,
            "chunks": [
                {"content": "c1", "page_number": 1, "chunk_index": 0,
                 "metadata": {"source": "test.pdf", "chunk_index": 0}},
                {"content": "c2", "page_number": 1, "chunk_index": 1,
                 "metadata": {"source": "test.pdf", "chunk_index": 1}},
                {"content": "c3", "page_number": 2, "chunk_index": 2,
                 "metadata": {"source": "test.pdf", "chunk_index": 2}},
            ],
        }
        mock_emb_cls.return_value.embed_texts.return_value = [[0.1]] * 3

        stream, name = _pdf_file()
        data = {"file": (stream, name)}
        resp = client.post(
            f"/api/documents/upload/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data=data, content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "ready"

    def test_no_file_returns_400(self, client, headers, sample_collection):
        """A request without a file field returns 400."""
        resp = client.post(
            f"/api/documents/upload/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={}, content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_unsupported_type_returns_400(self, client, headers,
                                          sample_collection):
        """An unsupported file extension returns 400."""
        stream = io.BytesIO(b"not a pdf")
        resp = client.post(
            f"/api/documents/upload/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={"file": (stream, "data.xyz")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_collection_not_found(self, client, headers):
        """Upload to a non-existent collection returns 404."""
        stream, name = _pdf_file()
        resp = client.post(
            "/api/documents/upload/99999",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={"file": (stream, name)},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 404

    @patch("app.api.documents.upload_file_to_s3")
    @patch("app.api.documents.DocumentProcessor")
    def test_processing_error_returns_500(
        self, mock_proc_cls, mock_s3, client, headers, sample_collection,
    ):
        """If DocumentProcessor raises, the document status becomes 'error'."""
        mock_proc_cls.return_value.process_document.side_effect = (
            RuntimeError("parse fail")
        )
        stream, name = _pdf_file()
        resp = client.post(
            f"/api/documents/upload/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={"file": (stream, name)},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 500


# ── GET /api/documents/<id> ──────────────────────────────────────────────

class TestGetDocument:
    """Tests for GET /api/documents/<document_id>."""

    def test_found(self, client, headers, sample_document):
        """Returns 200 and the document dict."""
        resp = client.get(
            f"/api/documents/{sample_document.id}", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["id"] == sample_document.id

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent document."""
        resp = client.get("/api/documents/99999", headers=headers)
        assert resp.status_code == 404


# ── DELETE /api/documents/<id> ────────────────────────────────────────────

class TestDeleteDocument:
    """Tests for DELETE /api/documents/<document_id>."""

    @patch("app.api.documents.BM25Index")
    @patch("app.api.documents.EmbeddingService")
    @patch("app.api.documents.VectorStore")
    def test_deletes_document(self, mock_vs, mock_emb, mock_bm25, client,
                              headers, sample_document):
        """Returns success and removes from DB."""
        doc_id = sample_document.id
        resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert db.session.get(Document, doc_id) is None

    def test_not_found(self, client, headers):
        """Returns 404 for a non-existent document."""
        resp = client.delete("/api/documents/99999", headers=headers)
        assert resp.status_code == 404

    @patch("app.api.documents.BM25Index")
    @patch("app.api.documents.EmbeddingService")
    @patch("app.api.documents.VectorStore")
    def test_vector_cleanup_failure_is_tolerated(
        self, mock_vs, mock_emb, mock_bm25, client, headers, sample_document,
    ):
        """Errors during vector cleanup are logged but don't prevent deletion."""
        mock_vs.return_value.delete_document_vectors.side_effect = RuntimeError("fail")
        doc_id = sample_document.id
        resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200


# ── POST /api/documents/upload_url/<id> ──────────────────────────────────

class TestGetUploadUrl:
    """Tests for POST /api/documents/upload_url/<collection_id>."""

    @patch("app.api.documents.create_presigned_put_url")
    def test_returns_presigned_url(self, mock_presign, client, headers,
                                   sample_collection):
        """A valid PDF file returns a presigned upload URL."""
        mock_presign.return_value = "https://s3.example.com/upload?token=abc"
        stream, name = _pdf_file()
        resp = client.post(
            f"/api/documents/upload_url/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={"file": (stream, name)},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert "presigned_upload_put_url" in resp.get_json()

    def test_no_file_returns_400(self, client, headers, sample_collection):
        """No file field returns 400."""
        resp = client.post(
            f"/api/documents/upload_url/{sample_collection.id}",
            headers={k: v for k, v in headers.items()
                     if k != "Content-Type"},
            data={}, content_type="multipart/form-data",
        )
        assert resp.status_code == 400
