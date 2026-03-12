"""Tests for LLMService: client factory, generation, streaming, message conversion.

All LangChain provider classes are mocked so no API keys or network access are
required.
"""

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.llm_service import LLMService, AVAILABLE_MODELS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def llm():
    """A fresh LLMService instance with an empty client cache."""
    return LLMService()


# ── _get_client ──────────────────────────────────────────────────────────

class TestGetClient:
    """Tests for LLMService._get_client (provider factory + caching)."""

    @patch("app.services.llm_service.Config")
    def test_openai_client(self, mock_cfg, llm):
        """OpenAI provider creates a ChatOpenAI instance."""
        mock_cfg.OPENAI_API_KEY = "sk-test"
        with patch("app.services.llm_service.LLMService._get_client") as orig:
            orig.return_value = MagicMock()
            client = orig("openai", "gpt-4o")
            assert client is not None

    @pytest.mark.parametrize("provider", ["openai", "anthropic", "groq", "google"])
    def test_supported_providers(self, provider, llm):
        """Each supported provider can instantiate without error when patched."""
        provider_patches = {
            "openai": "langchain_openai.ChatOpenAI",
            "anthropic": "langchain_anthropic.ChatAnthropic",
            "groq": "langchain_groq.ChatGroq",
            "google": "langchain_google_genai.ChatGoogleGenerativeAI",
        }
        with patch(provider_patches[provider]) as mock_cls:
            mock_cls.return_value = MagicMock()
            client = llm._get_client(provider, "model-x")
            assert client is not None

    def test_unsupported_provider_raises(self, llm):
        """An unsupported provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            llm._get_client("unknown_provider", "model-x")

    def test_client_caching(self, llm):
        """Repeated calls with the same key return the cached client."""
        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = llm._get_client("openai", "gpt-4o", 0.1)
            c2 = llm._get_client("openai", "gpt-4o", 0.1)
            assert c1 is c2
            assert mock_cls.call_count == 1

    def test_different_temperature_creates_new_client(self, llm):
        """A different temperature yields a separate cached entry."""
        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            llm._get_client("openai", "gpt-4o", 0.1)
            llm._get_client("openai", "gpt-4o", 0.9)
            assert mock_cls.call_count == 2


# ── generate ─────────────────────────────────────────────────────────────

class TestGenerate:
    """Tests for LLMService.generate (non-streaming)."""

    def test_returns_content_string(self, llm):
        """generate returns the text content of the LLM response."""
        mock_response = MagicMock()
        mock_response.content = "Generated answer."
        with patch.object(llm, "_get_client") as mock_get:
            mock_get.return_value.invoke.return_value = mock_response
            result = llm.generate(
                [{"role": "user", "content": "Hi"}],
                provider="openai",
                model_name="gpt-4o",
            )
        assert result == "Generated answer."

    def test_uses_default_provider(self, llm):
        """When provider is None, the configured default is used."""
        mock_response = MagicMock()
        mock_response.content = "ok"
        with patch.object(llm, "_get_client") as mock_get:
            mock_get.return_value.invoke.return_value = mock_response
            llm.generate([{"role": "user", "content": "Hi"}])
            call_args = mock_get.call_args
            assert call_args is not None


# ── generate_stream ──────────────────────────────────────────────────────

class TestGenerateStream:
    """Tests for LLMService.generate_stream (streaming)."""

    def test_yields_token_strings(self, llm):
        """generate_stream yields content strings from streamed chunks."""
        chunk1 = MagicMock()
        chunk1.content = "Hello"
        chunk2 = MagicMock()
        chunk2.content = " World"

        with patch.object(llm, "_get_client") as mock_get:
            mock_get.return_value.stream.return_value = iter([chunk1, chunk2])
            tokens = list(llm.generate_stream(
                [{"role": "user", "content": "Hi"}],
                provider="openai",
                model_name="gpt-4o",
            ))

        assert tokens == ["Hello", " World"]

    def test_skips_empty_chunks(self, llm):
        """Chunks with empty content are not yielded."""
        chunk_empty = MagicMock()
        chunk_empty.content = ""
        chunk_ok = MagicMock()
        chunk_ok.content = "data"

        with patch.object(llm, "_get_client") as mock_get:
            mock_get.return_value.stream.return_value = iter([chunk_empty, chunk_ok])
            tokens = list(llm.generate_stream(
                [{"role": "user", "content": "Hi"}],
                provider="openai",
                model_name="gpt-4o",
            ))

        assert tokens == ["data"]


# ── _convert_messages ─────────────────────────────────────────────────────

class TestConvertMessages:
    """Tests for LLMService._convert_messages."""

    def test_system_message(self, llm):
        """A system role maps to SystemMessage."""
        result = llm._convert_messages([{"role": "system", "content": "sys"}])
        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)

    def test_user_message(self, llm):
        """A user role maps to HumanMessage."""
        result = llm._convert_messages([{"role": "user", "content": "hi"}])
        assert isinstance(result[0], HumanMessage)

    def test_assistant_message(self, llm):
        """An assistant role maps to AIMessage."""
        result = llm._convert_messages([{"role": "assistant", "content": "hey"}])
        assert isinstance(result[0], AIMessage)

    def test_mixed_roles(self, llm):
        """Multiple roles are converted in order."""
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = llm._convert_messages(msgs)
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)


# ── get_available_models ─────────────────────────────────────────────────

class TestGetAvailableModels:
    """Tests for LLMService.get_available_models (static)."""

    @patch("app.services.llm_service.Config")
    def test_returns_only_configured_providers(self, mock_cfg):
        """Only providers with non-empty API keys appear."""
        mock_cfg.OPENAI_API_KEY = "sk-abc"
        mock_cfg.ANTHROPIC_API_KEY = ""
        mock_cfg.GROQ_API_KEY = ""
        mock_cfg.GEMINI_API_KEY = "gk-abc"
        result = LLMService.get_available_models()
        assert "openai" in result
        assert "google" in result
        assert "anthropic" not in result
        assert "groq" not in result

    @patch("app.services.llm_service.Config")
    def test_empty_keys_returns_empty(self, mock_cfg):
        """No providers when all API keys are empty."""
        mock_cfg.OPENAI_API_KEY = ""
        mock_cfg.ANTHROPIC_API_KEY = ""
        mock_cfg.GROQ_API_KEY = ""
        mock_cfg.GEMINI_API_KEY = ""
        assert LLMService.get_available_models() == {}
