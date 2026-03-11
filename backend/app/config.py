"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv
from sqlalchemy.util import osx

load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # Database
    SQLALCHEMY_DATABASE_URI = f"postgresql://postgres:{os.getenv("POSTGRES_PASSWORD")}@localhost/bookragdb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data/uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
    MAX_QUESTION_LENGTH = 500 #500 characters
    # BM25
    BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_indices")

    # Embedding model
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")

    # Reranker model
    RERANKER_MODEL_NAME = os.getenv(
        "RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # LLM providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "google")
    DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gemini-2.5-flash")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # RAG settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
    TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))
    CHAT_HISTORY_WINDOW = int(os.getenv("CHAT_HISTORY_WINDOW", "10"))
    
    # Observability (Langfuse)
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    TESSERACT_EXE_PATH = os.getenv("TESSERACT_EXE_PATH","")

    S3_BUCKET = os.getenv("S3_BUCKET","amzn-s3-bookrag-bucket")