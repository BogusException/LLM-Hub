"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AdapterResponse:
    """Normalized response from any LLM adapter."""
    text: str
    usage_input_tokens: int
    usage_output_tokens: int
    latency_ms: float


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    def __init__(self, api_key: str, model: str):
        """Initialize adapter with API key and model name.

        Args:
            api_key: Provider-specific API key
            model: Model identifier (e.g., 'gpt-4', 'claude-3-sonnet', 'gemini-1.5-pro')
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AdapterResponse:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Standard roles: 'system', 'user', 'assistant'
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            AdapterResponse with text, token usage, and latency

        Raises:
            RuntimeError: If API call fails or returns an error
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
