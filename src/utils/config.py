"""Configuration loading and validation using TOML."""

import os
from pathlib import Path
from typing import Any, Optional
import tomllib  # Python 3.11+
from .debug import get_debug_logger


def load_config_value(value: Any, base_path: Path) -> Any:
    """Load a config value, handling file references.

    If a value is a string starting with 'file://', load from that file.
    Otherwise return the value as-is.

    Args:
        value: Config value (might be string with 'file://' prefix)
        base_path: Base directory for relative paths

    Returns:
        Loaded value or original value

    Raises:
        ValueError: If file reference points to non-existent file
    """
    if isinstance(value, str) and value.startswith("file://"):
        filepath = value[7:]  # Remove 'file://' prefix
        if not Path(filepath).is_absolute():
            filepath = base_path / filepath

        if not Path(filepath).exists():
            raise ValueError(f"File reference points to non-existent file: {filepath}")

        try:
            with open(filepath, "r") as f:
                content = f.read()
                get_debug_logger().debug(f"Loaded config value from file: {filepath} ({len(content)} chars)")
                return content
        except IOError as e:
            raise ValueError(f"Failed to load file {filepath}: {e}") from e

    return value


class ConfigLoader:
    """Load and validate LAN-LLM-Hub configuration."""

    def __init__(self, config_path: str):
        """Initialize loader with config file path.

        Args:
            config_path: Path to TOML config file

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        self.config_path = Path(config_path)
        self.base_path = self.config_path.parent

        debug = get_debug_logger()
        debug.info(f"Initializing ConfigLoader with path: {config_path}")

        if not self.config_path.exists():
            debug.error(f"Config file not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")

        debug.debug(f"Config file exists: {self.config_path.absolute()}")

    def load(self) -> dict[str, Any]:
        """Load and parse config.

        Returns:
            Config dict with all sections and substitutions applied

        Raises:
            ValueError: If config is invalid or required sections missing
        """
        debug = get_debug_logger()
        debug.info("Loading config from TOML file")

        try:
            with open(self.config_path, "rb") as f:
                config = tomllib.load(f)
            debug.debug(f"Successfully parsed TOML file")
        except Exception as e:
            debug.error(f"Failed to parse TOML config", exc=e)
            raise ValueError(f"Failed to parse config file: {e}") from e

        try:
            # Process file:// references in all string values
            debug.debug("Processing file:// references in config values")
            config = self._process_file_refs(config)

            # Validate required sections
            debug.debug("Validating config structure")
            self._validate_config(config)

            debug.info(f"Config loaded successfully with {len(config.get('agents', []))} agents")
            return config
        except Exception as e:
            debug.error(f"Config validation failed", exc=e)
            raise

    def _process_file_refs(self, obj: Any) -> Any:
        """Recursively process file:// references in config object."""
        if isinstance(obj, dict):
            return {k: self._process_file_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._process_file_refs(item) for item in obj]
        elif isinstance(obj, str):
            return load_config_value(obj, self.base_path)
        else:
            return obj

    def _validate_config(self, config: dict) -> None:
        """Validate config has required sections.

        Raises:
            ValueError: If required sections are missing
        """
        if "session" not in config:
            raise ValueError("Config missing [session] section")
        if "agents" not in config or not config["agents"]:
            raise ValueError("Config missing [[agents]] entries")

    @staticmethod
    def get_session_config(config: dict) -> dict:
        """Extract session config.

        Args:
            config: Full config dict

        Returns:
            Session config dict with defaults applied
        """
        session = config.get("session", {})
        return {
            "log_dir": session.get("log_dir", "./logs"),
            "topology": session.get("topology", "hub_spoke"),
            "fanout": session.get("fanout", "broadcast_except_sender"),
            "keep_last_messages": session.get("keep_last_messages", 12),
            "summarize_after_messages": session.get("summarize_after_messages", 24),
            "max_turns_total": session.get("max_turns_total", 100),
            "max_minutes": session.get("max_minutes", 60.0),
            "max_tokens_total": session.get("max_tokens_total", 100000),
            "max_turns_per_agent": session.get("max_turns_per_agent"),
            "cooldown_seconds": session.get("cooldown_seconds", 0.0),
        }

    @staticmethod
    def get_agents_config(config: dict) -> list[dict]:
        """Extract and validate agents config.

        Args:
            config: Full config dict

        Returns:
            List of agent configs with defaults applied

        Raises:
            ValueError: If agent config is invalid
        """
        debug = get_debug_logger()
        agents = config.get("agents", [])
        validated = []

        debug.debug(f"Processing {len(agents)} agents from config")

        for idx, agent in enumerate(agents):
            try:
                # Validate required fields
                if "id" not in agent:
                    raise ValueError("Agent missing 'id' field")
                if "provider" not in agent:
                    raise ValueError(f"Agent (index {idx}) missing 'provider' field")
                if "model" not in agent:
                    raise ValueError(f"Agent (index {idx}) missing 'model' field")

                agent_id = agent["id"]
                provider = agent["provider"].lower()

                # Resolve API key: config → env var → error
                api_key = agent.get("api_key") or os.environ.get(
                    f"{provider.upper()}_KEY"
                )
                if not api_key:
                    raise ValueError(
                        f"Agent '{agent_id}' missing API key. "
                        f"Provide in config as api_key or set {provider.upper()}_KEY env var"
                    )

                # Resolve system prompt: prefer system_prompt_file if provided, else system_prompt
                system_prompt = agent.get("system_prompt", "")
                if agent.get("system_prompt_file"):
                    # system_prompt_file was already loaded by recursive file:// processing
                    system_prompt = agent.get("system_prompt_file")
                    debug.debug(f"Agent '{agent_id}': using system_prompt from file")

                agent_config = {
                    "id": agent_id,
                    "role": agent.get("role", "participant"),
                    "provider": provider,
                    "model": agent["model"],
                    "api_key": api_key,
                    "temperature": agent.get("temperature", 0.7),
                    "max_tokens": agent.get("max_tokens", 2000),
                    "attitude": agent.get("attitude", ""),
                    "system_prompt": system_prompt,
                    "subscriptions": agent.get("subscriptions", ["main"]),
                    "private_notes": agent.get("private_notes", False),
                }

                debug.debug(f"Agent '{agent_id}': {provider}/{agent['model']}, role={agent_config['role']}")
                validated.append(agent_config)

            except (KeyError, ValueError) as e:
                debug.error(f"Invalid agent config at index {idx}", exc=e)
                raise ValueError(f"Invalid agent config at index {idx}: {e}") from e

        debug.info(f"Successfully validated {len(validated)} agents")
        return validated
