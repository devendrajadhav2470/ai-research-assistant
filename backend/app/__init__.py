"""Flask application factory."""

import os
import boto3
from flask import Flask
from app.config import Config
from app.extensions import db, cors
import chromadb
import logging 
import torch

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    #Configure Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    # Ensure data directories exist
    os.makedirs(os.path.dirname(os.path.abspath(app.config["SQLITE_DB_PATH"])), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": ["http://localhost:3000","http://devendrajadhav.space"]}})

    # Initialize chroma db client 
    app.extensions['chroma_client'] = chromadb.PersistentClient(path="./chroma_data") 

    app.extensions['s3'] = boto3.client("s3")

    if torch.cuda.is_available():
        app.extensions['device'] = "cuda"
    else:
        app.extensions['device'] = 'cpu'
    # Register blueprints
    from app.api.documents import documents_bp
    from app.api.collections import collections_bp
    from app.api.chat import chat_bp
    from app.api.evaluation import evaluation_bp
    from app.api.config import config_bp
    from app.api.retrieval import retrieval_bp
    from app.api.auth import auth_bp
    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(collections_bp, url_prefix="/api/collections")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(evaluation_bp, url_prefix="/api/evaluation")
    app.register_blueprint(config_bp, url_prefix="/api/config")
    app.register_blueprint(retrieval_bp,url_prefix="/api/retrieval")
    app.register_blueprint(auth_bp,url_prefix="/api/auth")
    # Create database tables
    with app.app_context():
        from app.models.document import Collection, Document, Chunk  # noqa: F401
        from app.models.chat import Conversation, Message  # noqa: F401

        db.create_all()

    # Health check endpoint
    @app.route("/api/health")
    def health():
        return {"status": "healthy", "service": "ai-research-assistant"}

    return app
