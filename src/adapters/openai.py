"""OpenAI (ChatGPT) adapter."""

import time
import requests
from .base import LLMAdapter, AdapterResponse
from src.utils.debug import get_debug_logger


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI API (ChatGPT models)."""

    API_BASE = "https://api.openai.com/v1"

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AdapterResponse:
        """Generate response via OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            AdapterResponse with text, token usage, and latency

        Raises:
            RuntimeError: If API call fails or response is malformed
        """
        debug = get_debug_logger()
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            debug.debug(f"OpenAI: calling {self.model} with {len(messages)} messages")
            response = requests.post(
                f"{self.API_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            debug.debug(f"OpenAI: received response (status {response.status_code})")
        except requests.exceptions.Timeout as e:
            debug.error(f"OpenAI: API timeout after 60s", exc=e)
            raise RuntimeError(f"OpenAI API timeout: {e}") from e
        except requests.exceptions.HTTPError as e:
            debug.error(f"OpenAI: HTTP error {response.status_code}", exc=e)
            raise RuntimeError(f"OpenAI API HTTP error {response.status_code}: {e}") from e
        except requests.exceptions.RequestException as e:
            debug.error(f"OpenAI: request failed", exc=e)
            raise RuntimeError(f"OpenAI API error: {e}") from e

        try:
            data = response.json()
        except Exception as e:
            debug.error(f"OpenAI: failed to parse JSON response", exc=e)
            raise RuntimeError(f"OpenAI: invalid JSON response: {e}") from e

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            debug.error(f"OpenAI API returned error: {error_msg}")
            raise RuntimeError(f"OpenAI API error: {error_msg}")

        try:
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            latency_ms = (time.time() - start_time) * 1000

            debug.debug(f"OpenAI: generated {len(text)} chars in {latency_ms:.0f}ms")
            return AdapterResponse(
                text=text,
                usage_input_tokens=usage.get("prompt_tokens", 0),
                usage_output_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError) as e:
            debug.error(f"OpenAI: unexpected response format", exc=e)
            raise RuntimeError(f"OpenAI: unexpected response format: {e}") from e
