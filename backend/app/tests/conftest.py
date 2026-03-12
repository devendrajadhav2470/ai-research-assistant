"""Shared test fixtures for the backend test suite.

Provides a Flask test application backed by in-memory SQLite, pre-configured
auth bypass helpers, model factories, and common service mocks so that every
test module starts from a consistent, isolated baseline.
"""

import uuid

import numpy as np
import pytest
import sqlalchemy as sa
from flask import Flask, g
from unittest.mock import MagicMock

from app.extensions import db, cors

# ---------------------------------------------------------------------------
# Constants reused across tests
# ---------------------------------------------------------------------------

SAMPLE_USER_ID = "test-user-00000001"
SAMPLE_USER_EMAIL = "test@example.com"
SAMPLE_USER_PAYLOAD = {
    "email": SAMPLE_USER_EMAIL,
    "id": SAMPLE_USER_ID,
    "exp": 9999999999,
}
SAMPLE_GUEST_SESSION_ID = "guest-session-abc123"


# ---------------------------------------------------------------------------
# Test configuration (SQLite in-memory, no external services)
# ---------------------------------------------------------------------------

class TestConfig:
    """Mirrors production Config with safe defaults for testing."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    DEBUG = False

    UPLOAD_FOLDER = "/tmp/test_uploads"
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    MAX_QUESTION_LENGTH = 500

    BM25_INDEX_DIR = "/tmp/test_bm25"
    EMBEDDING_MODEL_NAME = "test-model"
    RERANKER_MODEL_NAME = "test-reranker"

    OPENAI_API_KEY = ""
    ANTHROPIC_API_KEY = ""
    GROQ_API_KEY = ""
    GEMINI_API_KEY = ""
    DEFAULT_LLM_PROVIDER = "openai"
    DEFAULT_MODEL_NAME = "gpt-4o"

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    TOP_K_RETRIEVAL = 20
    TOP_K_RERANK = 5
    CHAT_HISTORY_WINDOW = 10

    LANGFUSE_PUBLIC_KEY = ""
    LANGFUSE_SECRET_KEY = ""
    LANGFUSE_HOST = "https://cloud.langfuse.com"

    TESSERACT_EXE_PATH = ""
    S3_BUCKET = "test-bucket"


# ---------------------------------------------------------------------------
# Session-scoped patches
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _patch_pg_array():
    """Replace the PostgreSQL ARRAY column on Chunk with plain Text so that
    SQLite can create the table without errors."""
    from app.models.document import Chunk

    Chunk.__table__.c.chunk_tokens.type = sa.Text()


# ---------------------------------------------------------------------------
# Singleton cleanup (autouse – runs for every test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singletons():
    """Prevent singleton state from leaking between tests."""
    yield
    from app.services.embedding_service import EmbeddingService
    from app.services.bm25_index import BM25Index

    EmbeddingService._instance = None
    EmbeddingService._model = None
    BM25Index._instance = None


# ---------------------------------------------------------------------------
# Application factory (function-scoped for full isolation)
# ---------------------------------------------------------------------------

def _build_test_app() -> Flask:
    """Construct a Flask app wired for testing."""
    test_app = Flask(__name__)
    test_app.config.from_object(TestConfig)

    db.init_app(test_app)
    cors.init_app(test_app)

    test_app.extensions["chroma_client"] = MagicMock()
    test_app.extensions["s3"] = MagicMock()
    test_app.extensions["device"] = "cpu"

    from app.api.auth import auth_bp
    from app.api.collections import collections_bp
    from app.api.documents import documents_bp
    from app.api.chat import chat_bp
    from app.api.evaluation import evaluation_bp
    from app.api.config import config_bp
    from app.api.retrieval import retrieval_bp

    for bp, prefix in [
        (auth_bp, "/api/auth"),
        (collections_bp, "/api/collections"),
        (documents_bp, "/api/documents"),
        (chat_bp, "/api/chat"),
        (evaluation_bp, "/api/evaluation"),
        (config_bp, "/api/config"),
        (retrieval_bp, "/api/retrieval"),
    ]:
        test_app.register_blueprint(bp, url_prefix=prefix)

    @test_app.route("/api/health")
    def health():
        return {"status": "healthy", "service": "ai-research-assistant"}

    return test_app


@pytest.fixture
def app():
    """Create a fresh Flask test app with an empty in-memory database."""
    _app = _build_test_app()
    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client bound to the test app."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers():
    """Standard Authorization headers for authenticated API requests."""
    return {"Authorization": "test-token", "Content-Type": "application/json"}


@pytest.fixture
def guest_headers():
    """Guest session headers for unauthenticated guest API requests."""
    return {
        "GuestUserSessionId": SAMPLE_GUEST_SESSION_ID,
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_auth(monkeypatch):
    """Patch UserService so that ``token_required`` always succeeds."""
    monkeypatch.setattr(
        "app.services.user_service.UserService.decode_token",
        lambda self, token: dict(SAMPLE_USER_PAYLOAD),
    )
    _guest = MagicMock()
    _guest.email = f"guest_{SAMPLE_GUEST_SESSION_ID}@temporary.com"
    _guest.id = "guest-user-id"
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_guest_user",
        lambda self, sid: _guest,
    )


# ---------------------------------------------------------------------------
# Request context with g.user (for service-level tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def user_context(app):
    """Push a test request context with ``g.user`` pre-populated."""
    with app.test_request_context():
        g.user = dict(SAMPLE_USER_PAYLOAD)
        yield


# ---------------------------------------------------------------------------
# Model factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user(app):
    """Insert and return a sample User row."""
    from app.models.user import User, Status

    user = User(
        id=SAMPLE_USER_ID,
        email=SAMPLE_USER_EMAIL,
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash..",
        status=Status.ACTIVE,
        guest_user_session_id=str(uuid.uuid4()),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_collection(sample_user):
    """Insert and return a sample Collection row."""
    from app.models.document import Collection

    coll = Collection(
        name="Test Collection",
        description="For testing",
        user_id=sample_user.id,
    )
    db.session.add(coll)
    db.session.commit()
    return coll


@pytest.fixture
def sample_document(sample_collection):
    """Insert and return a sample Document row."""
    from app.models.document import Document

    doc = Document(
        collection_id=sample_collection.id,
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        page_count=5,
        chunk_count=10,
        status="ready",
    )
    db.session.add(doc)
    db.session.commit()
    return doc


@pytest.fixture
def sample_conversation(sample_collection, sample_user):
    """Insert and return a sample Conversation row."""
    from app.models.chat import Conversation

    conv = Conversation(
        collection_id=sample_collection.id,
        title="Test Conversation",
        user_id=sample_user.id,
    )
    db.session.add(conv)
    db.session.commit()
    return conv


@pytest.fixture
def sample_message(sample_conversation):
    """Insert and return a sample assistant Message row."""
    from app.models.chat import Message

    msg = Message(
        conversation_id=sample_conversation.id,
        role="assistant",
        content="Test answer from the assistant.",
        model_name="gpt-4o",
        provider="openai",
    )
    db.session.add(msg)
    db.session.commit()
    return msg


# ---------------------------------------------------------------------------
# Common service mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_embedding_service():
    """Fully mocked EmbeddingService (no model loading)."""
    mock = MagicMock()
    mock.embed_texts.return_value = np.random.randn(3, 768).astype(np.float32)
    mock.embed_query.return_value = np.random.randn(768).astype(np.float32)
    mock.dimension = 768
    mock.get_embedding_model.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_llm_service():
    """Fully mocked LLMService (no API calls)."""
    mock = MagicMock()
    mock.generate.return_value = "Test answer from LLM."
    mock.generate_stream.return_value = iter(["Test ", "answer ", "from ", "LLM."])
    return mock
