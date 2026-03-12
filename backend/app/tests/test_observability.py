"""Tests for the observability utility module: Langfuse integration.

All Langfuse imports and network calls are fully mocked.
"""

import pytest
from unittest.mock import patch, MagicMock

import app.utils.observability as obs


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset module-level globals before each test."""
    obs._langfuse_handler = None
    obs._langfuse_enabled = False
    yield
    obs._langfuse_handler = None
    obs._langfuse_enabled = False


# ── init_langfuse ────────────────────────────────────────────────────────

class TestInitLangfuse:
    """Tests for init_langfuse."""

    @patch("app.utils.observability.Config")
    def test_not_configured(self, mock_cfg):
        """Returns None when keys are empty."""
        mock_cfg.LANGFUSE_PUBLIC_KEY = ""
        mock_cfg.LANGFUSE_SECRET_KEY = ""
        result = obs.init_langfuse()
        assert result is None
        assert obs._langfuse_enabled is False

    @patch("app.utils.observability.Config")
    def test_configured_successfully(self, mock_cfg):
        """Returns a handler when keys are set and import succeeds."""
        mock_cfg.LANGFUSE_PUBLIC_KEY = "pk-test"
        mock_cfg.LANGFUSE_SECRET_KEY = "sk-test"
        mock_cfg.LANGFUSE_HOST = "https://langfuse.example.com"

        mock_handler = MagicMock()
        with patch.dict("sys.modules", {"langfuse": MagicMock(),
                                         "langfuse.callback": MagicMock()}):
            with patch("langfuse.callback.CallbackHandler",
                       return_value=mock_handler):
                result = obs.init_langfuse()

        assert result is mock_handler
        assert obs._langfuse_enabled is True

    @patch("app.utils.observability.Config")
    def test_import_error(self, mock_cfg):
        """Returns None when the langfuse package is not installed."""
        mock_cfg.LANGFUSE_PUBLIC_KEY = "pk-test"
        mock_cfg.LANGFUSE_SECRET_KEY = "sk-test"
        mock_cfg.LANGFUSE_HOST = "https://example.com"

        with patch.dict("sys.modules", {"langfuse": None,
                                         "langfuse.callback": None}):
            # Force ImportError by patching __import__
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
            def _fail_import(name, *args, **kwargs):
                if "langfuse" in name:
                    raise ImportError("no langfuse")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=_fail_import):
                result = obs.init_langfuse()

        assert result is None
        assert obs._langfuse_enabled is False

    @patch("app.utils.observability.Config")
    def test_unexpected_exception(self, mock_cfg):
        """Returns None on unexpected init errors."""
        mock_cfg.LANGFUSE_PUBLIC_KEY = "pk"
        mock_cfg.LANGFUSE_SECRET_KEY = "sk"
        mock_cfg.LANGFUSE_HOST = "https://example.com"

        with patch.dict("sys.modules", {"langfuse": MagicMock(),
                                         "langfuse.callback": MagicMock()}):
            with patch("langfuse.callback.CallbackHandler",
                       side_effect=RuntimeError("boom")):
                result = obs.init_langfuse()

        assert result is None
        assert obs._langfuse_enabled is False


# ── get_langfuse_handler ─────────────────────────────────────────────────

class TestGetLangfuseHandler:
    """Tests for get_langfuse_handler."""

    def test_returns_none_when_disabled(self):
        """Returns None when observability is disabled."""
        assert obs.get_langfuse_handler() is None

    def test_returns_handler_when_set(self):
        """Returns the handler if it was previously initialised."""
        fake = MagicMock()
        obs._langfuse_handler = fake
        obs._langfuse_enabled = True
        assert obs.get_langfuse_handler() is fake


# ── get_langfuse_callbacks ───────────────────────────────────────────────

class TestGetLangfuseCallbacks:
    """Tests for get_langfuse_callbacks."""

    def test_empty_when_disabled(self):
        """Returns an empty list when no handler is configured."""
        assert obs.get_langfuse_callbacks() == []

    def test_list_with_handler(self):
        """Returns a single-element list containing the handler."""
        fake = MagicMock()
        obs._langfuse_handler = fake
        obs._langfuse_enabled = True
        assert obs.get_langfuse_callbacks() == [fake]


# ── is_enabled ───────────────────────────────────────────────────────────

class TestIsEnabled:
    """Tests for is_enabled."""

    def test_false_by_default(self):
        """Disabled by default."""
        assert obs.is_enabled() is False

    def test_true_when_enabled(self):
        """True after successful init."""
        obs._langfuse_enabled = True
        assert obs.is_enabled() is True


# ── trace_event ──────────────────────────────────────────────────────────

class TestTraceEvent:
    """Tests for trace_event."""

    def test_noop_when_disabled(self):
        """Does nothing (no error) when disabled."""
        obs.trace_event("test_event", {"key": "value"})

    def test_runs_when_enabled(self):
        """Executes without error when enabled with a handler."""
        obs._langfuse_enabled = True
        obs._langfuse_handler = MagicMock()
        obs.trace_event("test_event", {"key": "value"})
