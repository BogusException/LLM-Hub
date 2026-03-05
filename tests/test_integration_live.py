"""Integration tests with live API calls.

These tests use real config.toml and make actual API calls to validate
that agents are properly configured and can connect to their providers.

This test file is NOT run in CI/CD by default (no live API keys available).
Run manually to validate your configuration:
    pytest tests/test_integration_live.py -v
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import ConfigLoader
from src.session import Session


class TestLiveConfiguration:
    """Test that config.toml exists and is valid."""

    @pytest.fixture(scope="class")
    def config_path(self):
        """Get path to config.toml."""
        return Path(__file__).parent.parent / "config.toml"

    def test_config_file_exists(self, config_path):
        """Check if config.toml exists. Skip if not (expected for CI/CD)."""
        if not config_path.exists():
            pytest.skip("config.toml not found (expected in CI/CD environment)")
        assert config_path.exists(), f"config.toml not found at {config_path}"

    def test_config_loads_successfully(self, config_path):
        """Load config and validate structure."""
        if not config_path.exists():
            pytest.skip("config.toml not found")

        loader = ConfigLoader(str(config_path))
        config = loader.load()

        # Validate structure
        assert "session" in config, "Missing [session] section"
        assert "agents" in config, "Missing [[agents]] section"
        assert len(config["agents"]) > 0, "No agents defined"

    def test_agents_have_required_fields(self, config_path):
        """Validate that all agents have required configuration."""
        if not config_path.exists():
            pytest.skip("config.toml not found")

        loader = ConfigLoader(str(config_path))
        config = loader.load()

        required_fields = ["id", "provider", "model"]
        for idx, agent in enumerate(config["agents"]):
            for field in required_fields:
                assert field in agent, f"Agent {idx} missing required field: {field}"

            assert agent["provider"].lower() in ["openai", "google", "anthropic"], \
                f"Agent {agent['id']}: unknown provider '{agent['provider']}'"


class TestLiveAgents:
    """Test agent connectivity and API calls with live providers."""

    @pytest.fixture(scope="class")
    def config_path(self):
        """Get path to config.toml."""
        return Path(__file__).parent.parent / "config.toml"

    @pytest.fixture(scope="class")
    def session(self, config_path):
        """Create session with live config."""
        if not config_path.exists():
            pytest.skip("config.toml not found")

        loader = ConfigLoader(str(config_path))
        config = loader.load()

        try:
            session = Session(config, start_prompt="Test session initialization")
            yield session
        except Exception as e:
            pytest.fail(
                f"Failed to initialize session with config.toml:\n"
                f"{str(e)}\n"
                f"Check logs/debug.log for detailed error information"
            )

    def test_session_created(self, session):
        """Verify session was created successfully."""
        if session is None:
            pytest.skip("Session creation skipped (no config)")
        assert session is not None
        assert session.session_id is not None
        assert len(session.get_all_agents()) > 0

    def test_all_agents_have_adapters(self, session):
        """Verify all agents have adapters initialized."""
        if session is None:
            pytest.skip("Session creation skipped (no config)")

        for agent in session.get_all_agents():
            assert agent.adapter is not None, \
                f"Agent {agent.id} missing adapter"

    def test_single_api_call_per_agent(self, session):
        """Test that each agent can make a successful API call.

        This is the critical test: if config.toml exists and agents are
        configured, API calls MUST succeed. If they fail, we report detailed
        diagnostics.
        """
        if session is None:
            pytest.skip("Session creation skipped (no config)")

        agents = session.get_all_agents()
        assert len(agents) > 0, "No agents in session"

        failed_agents = []

        for agent in agents:
            try:
                # Create a minimal message context
                messages = [{"role": "user", "content": "Respond with: OK"}]

                # Call adapter
                response = agent.adapter.generate(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=100,
                )

                # Verify response structure
                assert response is not None, f"Agent {agent.id}: null response"
                assert response.text is not None, f"Agent {agent.id}: null text"
                assert len(response.text) > 0, f"Agent {agent.id}: empty response"
                assert response.usage_input_tokens >= 0, f"Agent {agent.id}: invalid input tokens"
                assert response.usage_output_tokens >= 0, f"Agent {agent.id}: invalid output tokens"

            except Exception as e:
                error_msg = str(e)
                failed_agents.append({
                    "agent_id": agent.id,
                    "provider": agent.provider,
                    "model": agent.model,
                    "error": error_msg,
                })

        # Report detailed diagnostics if any agent failed
        if failed_agents:
            error_report = "Agent connectivity test FAILED. System configuration fault detected:\n\n"
            for agent_error in failed_agents:
                error_report += f"Agent: {agent_error['agent_id']}\n"
                error_report += f"  Provider: {agent_error['provider']}\n"
                error_report += f"  Model: {agent_error['model']}\n"
                error_report += f"  Error: {agent_error['error']}\n\n"

            error_report += "Troubleshooting steps:\n"
            error_report += "  1. Verify API keys in config.toml are valid and not expired\n"
            error_report += "  2. Check network connectivity to API endpoints\n"
            error_report += "  3. Verify model names match provider's available models:\n"
            error_report += "     - OpenAI: gpt-4, gpt-3.5-turbo, etc.\n"
            error_report += "     - Anthropic: claude-3-sonnet, claude-3-haiku, etc.\n"
            error_report += "     - Google: gemini-1.5-pro, gemini-1.5-flash, etc.\n"
            error_report += "  4. Check provider rate limits are not exceeded\n"
            error_report += "  5. Review logs/debug.log for API response details\n"

            pytest.fail(error_report)

    def test_api_call_produces_valid_response(self, session):
        """Test that a single agent produces a well-formed response."""
        if session is None:
            pytest.skip("Session creation skipped (no config)")

        agents = session.get_all_agents()
        if len(agents) == 0:
            pytest.skip("No agents configured")

        # Test first agent
        agent = agents[0]

        messages = [
            {"role": "user", "content": "Say the word 'success' only."}
        ]

        response = agent.adapter.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=50,
        )

        # Check response structure and content
        assert isinstance(response.text, str), "Response text is not a string"
        assert len(response.text) > 0, "Response text is empty"
        assert response.latency_ms > 0, "Latency not recorded"
        assert response.usage_input_tokens > 0, "Input tokens not recorded"
        # Output tokens might be 0 in rare cases, but should be recorded
        assert isinstance(response.usage_output_tokens, int), "Output tokens not recorded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
