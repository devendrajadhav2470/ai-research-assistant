"""Multi-provider LLM service via LangChain with streaming support."""

import logging
from typing import Generator, Optional, Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Config

logger = logging.getLogger(__name__)

# Available models per provider
AVAILABLE_MODELS = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B"},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
    ],
    "google": [
        {"id": "gemini-3-pro", "name": "Gemini 3 Pro"},
        {"id": "gemini-3-flash", "name": "Gemini 3 Flash"},
        {"id": "gemini-3-flash-lite", "name": "Gemini 3 Flash Lite"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    ],
}


class LLMService:
    """Factory for creating LLM instances across multiple providers."""

    def __init__(self):
        self._clients: Dict[str, BaseChatModel] = {}

    def _get_client(
        self, provider: str, model_name: str, temperature: float = 0.1
    ) -> BaseChatModel:
        """Get or create an LLM client for the given provider and model."""
        cache_key = f"{provider}:{model_name}:{temperature}"

        if cache_key not in self._clients:
            if provider == "openai":
                from langchain_openai import ChatOpenAI

                self._clients[cache_key] = ChatOpenAI(
                    model=model_name,
                    api_key=Config.OPENAI_API_KEY,
                    temperature=temperature,
                    streaming=True,
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                self._clients[cache_key] = ChatAnthropic(
                    model=model_name,
                    api_key=Config.ANTHROPIC_API_KEY,
                    temperature=temperature,
                    streaming=True,
                )
            elif provider == "groq":
                from langchain_groq import ChatGroq

                self._clients[cache_key] = ChatGroq(
                    model=model_name,
                    api_key=Config.GROQ_API_KEY,
                    temperature=temperature,
                    streaming=True,
                )
            elif provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._clients[cache_key] = ChatGoogleGenerativeAI(
                    model=model_name,
                    api_key=Config.GEMINI_API_KEY,
                    temperature=temperature,
                    streaming=True,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

            logger.info(f"Created LLM client: {provider}/{model_name}")

        return self._clients[cache_key]

    def generate(
        self,
        messages: List[Dict[str, str]],
        provider: str = None,
        model_name: str = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a complete response (non-streaming).

        Args:
            messages: List of message dicts with 'role' and 'content'.
            provider: LLM provider name.
            model_name: Model identifier.
            temperature: Sampling temperature.

        Returns:
            Generated text response.
        """
        provider = provider or Config.DEFAULT_LLM_PROVIDER
        model_name = model_name or Config.DEFAULT_MODEL_NAME
        client = self._get_client(provider, model_name, temperature)

        langchain_messages = self._convert_messages(messages)
        response = client.invoke(langchain_messages)
        return response.content

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        provider: str = None,
        model_name: str = None,
        temperature: float = 0.1,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response (token by token).

        Args:
            messages: List of message dicts with 'role' and 'content'.
            provider: LLM provider name.
            model_name: Model identifier.
            temperature: Sampling temperature.

        Yields:
            Text chunks as they are generated.
        """
        provider = provider or Config.DEFAULT_LLM_PROVIDER
        model_name = model_name or Config.DEFAULT_MODEL_NAME
        client = self._get_client(provider, model_name, temperature)

        langchain_messages = self._convert_messages(messages)

        for chunk in client.stream(langchain_messages):
            if chunk.content:
                yield chunk.content

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> list:
        """Convert simple message dicts to LangChain message objects."""
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
        return langchain_messages

    @staticmethod
    def get_available_models() -> Dict[str, list]:
        """Return available models grouped by provider, filtered by configured API keys."""
        available = {}
        if Config.OPENAI_API_KEY:
            available["openai"] = AVAILABLE_MODELS["openai"]
        if Config.ANTHROPIC_API_KEY:
            available["anthropic"] = AVAILABLE_MODELS["anthropic"]
        if Config.GROQ_API_KEY:
            available["groq"] = AVAILABLE_MODELS["groq"]
        if Config.GEMINI_API_KEY:
            available["google"] = AVAILABLE_MODELS["google"]
        return available

