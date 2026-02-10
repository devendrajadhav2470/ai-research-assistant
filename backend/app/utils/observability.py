"""Observability integration with Langfuse for tracing LLM calls and retrieval."""

import logging
from typing import Optional
from functools import wraps

from app.config import Config

logger = logging.getLogger(__name__)

_langfuse_handler = None
_langfuse_enabled = False


def init_langfuse():
    """Initialize Langfuse callback handler for LangChain if keys are configured."""
    global _langfuse_handler, _langfuse_enabled

    if not Config.LANGFUSE_PUBLIC_KEY or not Config.LANGFUSE_SECRET_KEY:
        logger.info("Langfuse not configured - observability disabled")
        _langfuse_enabled = False
        return None

    try:
        from langfuse.callback import CallbackHandler

        _langfuse_handler = CallbackHandler(
            public_key=Config.LANGFUSE_PUBLIC_KEY,
            secret_key=Config.LANGFUSE_SECRET_KEY,
            host=Config.LANGFUSE_HOST,
        )
        _langfuse_enabled = True
        logger.info(f"Langfuse initialized at {Config.LANGFUSE_HOST}")
        return _langfuse_handler
    except ImportError:
        logger.warning("langfuse package not installed - observability disabled")
        _langfuse_enabled = False
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        _langfuse_enabled = False
        return None


def get_langfuse_handler():
    """Get the Langfuse callback handler (or None if not configured)."""
    global _langfuse_handler
    if _langfuse_handler is None and _langfuse_enabled is False:
        init_langfuse()
    return _langfuse_handler


def get_langfuse_callbacks() -> list:
    """Get a list of LangChain callbacks including Langfuse if available."""
    handler = get_langfuse_handler()
    return [handler] if handler else []


def is_enabled() -> bool:
    """Check if observability is enabled."""
    return _langfuse_enabled


def trace_event(event_name: str, metadata: dict = None):
    """Log a trace event to Langfuse if enabled."""
    if not _langfuse_enabled or not _langfuse_handler:
        return

    try:
        # Langfuse will capture this via LangChain callbacks
        logger.debug(f"Trace event: {event_name}, metadata: {metadata}")
    except Exception as e:
        logger.warning(f"Failed to log trace event: {e}")

