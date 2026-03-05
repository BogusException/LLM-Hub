"""Anthropic Claude adapter."""

import time
import requests
from .base import LLMAdapter, AdapterResponse
from src.utils.debug import get_debug_logger


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude API."""

    API_BASE = "https://api.anthropic.com/v1"

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AdapterResponse:
        """Generate response via Anthropic API.

        Note: Anthropic API requires system messages to be separate from user messages,
        combined into a single 'system' parameter.

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
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            # Separate system messages from user messages
            system_messages = []
            user_messages = []

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_messages.append(content)
                else:
                    user_messages.append({"role": role, "content": content})

            # Combine system messages into a single system prompt
            system_prompt = "\n".join(system_messages) if system_messages else None

            payload = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                payload["system"] = system_prompt

            debug.debug(f"Anthropic: calling {self.model} with {len(user_messages)} messages")
            response = requests.post(
                f"{self.API_BASE}/messages",
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            debug.debug(f"Anthropic: received response (status {response.status_code})")
        except requests.exceptions.Timeout as e:
            debug.error(f"Anthropic: API timeout after 60s", exc=e)
            raise RuntimeError(f"Anthropic API timeout: {e}") from e
        except requests.exceptions.HTTPError as e:
            debug.error(f"Anthropic: HTTP error {response.status_code}", exc=e)
            raise RuntimeError(f"Anthropic API HTTP error {response.status_code}: {e}") from e
        except requests.exceptions.RequestException as e:
            debug.error(f"Anthropic: request failed", exc=e)
            raise RuntimeError(f"Anthropic API error: {e}") from e

        try:
            data = response.json()
        except Exception as e:
            debug.error(f"Anthropic: failed to parse JSON response", exc=e)
            raise RuntimeError(f"Anthropic: invalid JSON response: {e}") from e

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            debug.error(f"Anthropic API returned error: {error_msg}")
            raise RuntimeError(f"Anthropic API error: {error_msg}")

        try:
            text = data["content"][0]["text"]
            usage = data.get("usage", {})
            latency_ms = (time.time() - start_time) * 1000

            debug.debug(f"Anthropic: generated {len(text)} chars in {latency_ms:.0f}ms")
            return AdapterResponse(
                text=text,
                usage_input_tokens=usage.get("input_tokens", 0),
                usage_output_tokens=usage.get("output_tokens", 0),
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError) as e:
            debug.error(f"Anthropic: unexpected response format", exc=e)
            raise RuntimeError(f"Anthropic: unexpected response format: {e}") from e
