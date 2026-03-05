"""Google Gemini adapter."""

import time
import requests
from .base import LLMAdapter, AdapterResponse
from src.utils.debug import get_debug_logger


class GoogleAdapter(LLMAdapter):
    """Adapter for Google Gemini API."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AdapterResponse:
        """Generate response via Google Gemini API.

        Note: Google Gemini uses different message format with system instructions
        separate from regular messages.

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

        try:
            # Google Gemini uses a different message structure
            contents = []
            system_instruction = None

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    system_instruction = content
                else:
                    # Gemini uses 'user' and 'model' roles
                    gemini_role = "user" if role in ("user", "assistant") else role
                    contents.append({
                        "role": gemini_role,
                        "parts": [{"text": content}]
                    })

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }

            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            debug.debug(f"Google Gemini: calling {self.model} with {len(contents)} content blocks")
            response = requests.post(
                f"{self.API_BASE}/models/{self.model}:generateContent",
                json=payload,
                params={"key": self.api_key},
                timeout=60,
            )
            response.raise_for_status()
            debug.debug(f"Google Gemini: received response (status {response.status_code})")
        except requests.exceptions.Timeout as e:
            debug.error(f"Google Gemini: API timeout after 60s", exc=e)
            raise RuntimeError(f"Google Gemini API timeout: {e}") from e
        except requests.exceptions.HTTPError as e:
            debug.error(f"Google Gemini: HTTP error {response.status_code}", exc=e)
            raise RuntimeError(f"Google Gemini API HTTP error {response.status_code}: {e}") from e
        except requests.exceptions.RequestException as e:
            debug.error(f"Google Gemini: request failed", exc=e)
            raise RuntimeError(f"Google Gemini API error: {e}") from e

        try:
            data = response.json()
        except Exception as e:
            debug.error(f"Google Gemini: failed to parse JSON response", exc=e)
            raise RuntimeError(f"Google Gemini: invalid JSON response: {e}") from e

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            debug.error(f"Google Gemini API returned error: {error_msg}")
            raise RuntimeError(f"Google Gemini API error: {error_msg}")

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Google doesn't provide token counts in basic API
            usage_data = data.get("usageMetadata", {})
            latency_ms = (time.time() - start_time) * 1000

            debug.debug(f"Google Gemini: generated {len(text)} chars in {latency_ms:.0f}ms")
            return AdapterResponse(
                text=text,
                usage_input_tokens=usage_data.get("promptTokenCount", 0),
                usage_output_tokens=usage_data.get("candidatesTokenCount", 0),
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError) as e:
            debug.error(f"Google Gemini: unexpected response format", exc=e)
            raise RuntimeError(f"Google Gemini: unexpected response format: {e}") from e
