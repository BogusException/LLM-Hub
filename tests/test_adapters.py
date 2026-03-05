"""Tests for LLM adapters."""

import pytest
from unittest.mock import Mock, patch
from src.adapters import OpenAIAdapter, GoogleAdapter, AnthropicAdapter


class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    def test_init(self):
        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        assert adapter.api_key == "test-key"
        assert adapter.model == "gpt-4"

    @patch("src.adapters.openai.requests.post")
    def test_generate_success(self, mock_post):
        """Test successful generate call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_post.return_value = mock_response

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        result = adapter.generate(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
        )

        assert result.text == "Hello world"
        assert result.usage_input_tokens == 10
        assert result.usage_output_tokens == 5
        assert result.latency_ms > 0

    @patch("src.adapters.openai.requests.post")
    def test_generate_api_error(self, mock_post):
        """Test API error handling."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        with pytest.raises(RuntimeError):
            adapter.generate(messages=[{"role": "user", "content": "Hello"}])


class TestGoogleAdapter:
    """Tests for Google Gemini adapter."""

    def test_init(self):
        adapter = GoogleAdapter(api_key="test-key", model="gemini-1.5-pro")
        assert adapter.api_key == "test-key"
        assert adapter.model == "gemini-1.5-pro"

    @patch("src.adapters.google.requests.post")
    def test_generate_success(self, mock_post):
        """Test successful generate call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Hello Google"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
        }
        mock_post.return_value = mock_response

        adapter = GoogleAdapter(api_key="test-key", model="gemini-1.5-pro")
        result = adapter.generate(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
        )

        assert result.text == "Hello Google"
        assert result.usage_input_tokens == 10
        assert result.usage_output_tokens == 5


class TestAnthropicAdapter:
    """Tests for Anthropic Claude adapter."""

    def test_init(self):
        adapter = AnthropicAdapter(api_key="test-key", model="claude-3-sonnet")
        assert adapter.api_key == "test-key"
        assert adapter.model == "claude-3-sonnet"

    @patch("src.adapters.anthropic.requests.post")
    def test_generate_success(self, mock_post):
        """Test successful generate call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"text": "Hello Claude"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        mock_post.return_value = mock_response

        adapter = AnthropicAdapter(api_key="test-key", model="claude-3-sonnet")
        result = adapter.generate(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
        )

        assert result.text == "Hello Claude"
        assert result.usage_input_tokens == 10
        assert result.usage_output_tokens == 5
