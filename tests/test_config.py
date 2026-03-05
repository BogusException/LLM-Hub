"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path
import pytest
from src.utils.config import ConfigLoader, load_config_value


class TestConfigLoading:
    """Tests for config loading."""

    def test_load_basic_config(self):
        """Test loading a basic valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_content = """
[session]
topology = "hub_spoke"
max_turns_total = 50

[[agents]]
id = "agent1"
provider = "openai"
model = "gpt-4"
api_key = "test-key"
"""
            config_path.write_text(config_content)

            loader = ConfigLoader(str(config_path))
            config = loader.load()

            assert config["session"]["topology"] == "hub_spoke"
            assert len(config["agents"]) == 1
            assert config["agents"][0]["id"] == "agent1"

    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader("/nonexistent/path/config.toml")

    def test_missing_required_sections(self):
        """Test error when required sections are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_content = "[session]\ntopology = 'hub_spoke'"
            config_path.write_text(config_content)

            loader = ConfigLoader(str(config_path))
            with pytest.raises(ValueError):
                loader.load()  # Missing agents


class TestFileReferences:
    """Tests for file:// references in config."""

    def test_load_value_from_file(self):
        """Test loading a value from a file reference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            base_path = tmpdir

            # Create a file with some content
            content_file = tmpdir / "system_prompt.txt"
            content_file.write_text("You are a helpful assistant")

            # Test loading
            value = load_config_value("file://system_prompt.txt", base_path)
            assert value == "You are a helpful assistant"

    def test_load_absolute_file_reference(self):
        """Test loading from absolute file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            content_file = tmpdir / "prompt.txt"
            content_file.write_text("Absolute path content")

            value = load_config_value(f"file://{content_file}", tmpdir)
            assert value == "Absolute path content"

    def test_non_file_value_unchanged(self):
        """Test that non-file values are returned as-is."""
        value = load_config_value("just a string", Path("."))
        assert value == "just a string"

        value = load_config_value(42, Path("."))
        assert value == 42

    def test_missing_file_reference_error(self):
        """Test error when file reference points to non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                load_config_value("file://missing.txt", Path(tmpdir))


class TestSessionConfig:
    """Tests for session config extraction."""

    def test_session_config_defaults(self):
        """Test session config with defaults applied."""
        config = {
            "session": {
                "topology": "hub_spoke",
            },
            "agents": [{"id": "a1", "provider": "openai", "model": "gpt-4", "api_key": "key"}],
        }

        session_cfg = ConfigLoader.get_session_config(config)
        assert session_cfg["topology"] == "hub_spoke"
        assert session_cfg["log_dir"] == "./logs"
        assert session_cfg["keep_last_messages"] == 12
        assert session_cfg["max_turns_total"] == 100

    def test_session_config_override_defaults(self):
        """Test session config overriding defaults."""
        config = {
            "session": {
                "topology": "star",
                "max_turns_total": 500,
                "keep_last_messages": 20,
            },
            "agents": [{"id": "a1", "provider": "openai", "model": "gpt-4", "api_key": "key"}],
        }

        session_cfg = ConfigLoader.get_session_config(config)
        assert session_cfg["topology"] == "star"
        assert session_cfg["max_turns_total"] == 500
        assert session_cfg["keep_last_messages"] == 20


class TestAgentConfig:
    """Tests for agent config extraction."""

    def test_agent_config_required_fields(self):
        """Test that required agent fields are validated."""
        config = {
            "session": {},
            "agents": [
                {"id": "agent1", "provider": "openai", "model": "gpt-4", "api_key": "key"}
            ],
        }

        agents = ConfigLoader.get_agents_config(config)
        assert len(agents) == 1
        assert agents[0]["id"] == "agent1"
        assert agents[0]["provider"] == "openai"
        assert agents[0]["model"] == "gpt-4"

    def test_agent_config_missing_id(self):
        """Test error when agent is missing id."""
        config = {
            "session": {},
            "agents": [{"provider": "openai", "model": "gpt-4", "api_key": "key"}],
        }

        with pytest.raises(ValueError):
            ConfigLoader.get_agents_config(config)

    def test_agent_config_api_key_from_env(self):
        """Test loading API key from environment variable."""
        os.environ["OPENAI_API_KEY"] = "env-key"

        config = {
            "session": {},
            "agents": [{"id": "agent1", "provider": "openai", "model": "gpt-4"}],
        }

        agents = ConfigLoader.get_agents_config(config)
        assert agents[0]["api_key"] == "env-key"

    def test_agent_config_defaults(self):
        """Test agent config with defaults applied."""
        config = {
            "session": {},
            "agents": [
                {
                    "id": "agent1",
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "key",
                }
            ],
        }

        agents = ConfigLoader.get_agents_config(config)
        assert agents[0]["temperature"] == 0.7
        assert agents[0]["max_tokens"] == 2000
        assert agents[0]["attitude"] == ""
        assert agents[0]["private_notes"] is False
