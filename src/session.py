"""Session management and orchestration."""

from datetime import datetime
from typing import Optional
from src.adapters import (
    LLMAdapter, OpenAIAdapter, GoogleAdapter, AnthropicAdapter
)
from src.memory import AgentMemory
from src.router import Router, TopologyType
from src.guardrails import Guardrails
from src.utils.logging import SessionLogger
from src.utils.config import ConfigLoader
from src.utils.debug import get_debug_logger
from src.utils.stats import StatsCollector


class Agent:
    """Represents a single agent in the session.

    An agent is a distinct participant with:
    - A unique ID and role
    - A specific LLM provider/model pair
    - Its own bounded memory buffer
    - Optional persona ("attitude") and system prompt
    - Subscriptions to message channels

    Multiple agents can use the same model but have different personalities,
    system prompts, and memory buffers (they're independent participants).
    """

    def __init__(self, agent_config: dict, adapter: LLMAdapter):
        """Initialize agent.

        Args:
            agent_config: Agent configuration dict with keys: id, role, provider, model,
                         temperature, max_tokens, attitude, system_prompt, subscriptions, private_notes
            adapter: LLMAdapter instance for this agent (handles API calls)
        """
        self.id = agent_config["id"]
        self.role = agent_config.get("role", "participant")
        self.provider = agent_config["provider"]
        self.model = agent_config["model"]
        self.temperature = agent_config.get("temperature", 0.7)
        self.max_tokens = agent_config.get("max_tokens", 2000)
        self.attitude = agent_config.get("attitude", "")
        self.system_prompt = agent_config.get("system_prompt", "")
        self.subscriptions = agent_config.get("subscriptions", ["main"])
        self.private_notes = agent_config.get("private_notes", False)

        self.adapter = adapter
        self.memory = AgentMemory(agent_id=self.id)

    def get_system_prompt(self) -> str:
        """Get effective system prompt by composing base prompt + attitude.

        The effective system prompt is built as:
        1. Base system prompt (if loaded from file)
        2. Attitude directive (if configured)
        3. (Future) session constraints

        This allows flexible persona injection without modifying base prompts.

        Returns:
            Combined system prompt string (may be empty if no prompt or attitude)
        """
        prompts = []
        if self.system_prompt:
            prompts.append(self.system_prompt)
        if self.attitude:
            prompts.append(f"Attitude: {self.attitude}")
        return "\n".join(prompts) if prompts else ""

    def __repr__(self) -> str:
        return f"Agent({self.id}, {self.provider}/{self.model})"


class Session:
    """Orchestrates a multi-agent conversation session.

    A session brings together all components:
    - Agents (with their adapters and memory)
    - Router (for message flow)
    - Guardrails (for budgets and safety)
    - Logger (for session events)

    The session is created from a config dict and is ready to be orchestrated
    by the main hub loop. It handles agent creation, adapter initialization,
    router setup, and logging.
    """

    def __init__(self, config: dict, start_prompt: str = "", session_id: Optional[str] = None):
        """Initialize session from config.

        Args:
            config: Full config dict from ConfigLoader
            start_prompt: Optional initial prompt from user
            session_id: Optional session ID (generated if not provided)

        Raises:
            ValueError: If config is invalid or agents cannot be created
        """
        debug = get_debug_logger()
        self.config = config
        self.start_prompt = start_prompt
        self.session_id = session_id or datetime.now().strftime("%Y%m%d%H%M%S")

        debug.info(f"Creating session: {self.session_id}")

        try:
            # Extract config sections
            debug.debug("Extracting session config")
            session_cfg = ConfigLoader.get_session_config(config)

            debug.debug("Extracting agents config")
            agents_cfg = ConfigLoader.get_agents_config(config)

            # Initialize logger
            debug.debug(f"Initializing session logger")
            self.logger = SessionLogger(
                self.session_id,
                log_dir=session_cfg["log_dir"],
                enable_jsonl=True,
            )

            # Initialize stats collector
            debug.debug(f"Initializing stats collector")
            self.stats = StatsCollector(
                self.session_id,
                log_dir=session_cfg["log_dir"],
            )

            # Initialize agents
            debug.debug(f"Creating {len(agents_cfg)} agent instances")
            self.agents = {}
            self._create_agents(agents_cfg)
            debug.info(f"Successfully created {len(self.agents)} agents")

            # Initialize router
            try:
                topology = TopologyType(session_cfg["topology"])
                debug.debug(f"Initializing router with topology: {topology.value}")
            except ValueError as e:
                debug.error(f"Invalid topology: {session_cfg['topology']}", exc=e)
                raise ValueError(f"Invalid topology '{session_cfg['topology']}'. Must be one of: {', '.join(t.value for t in TopologyType)}") from e

            self.router = Router(
                topology=topology,
                agents=list(self.agents.keys()),
                fanout=session_cfg.get("fanout", "broadcast_except_sender"),
            )
            debug.debug(f"Router initialized with {len(self.agents)} agents")

            # Initialize guardrails
            debug.debug("Initializing guardrails")
            self.guardrails = Guardrails(
                max_turns_total=session_cfg.get("max_turns_total", 100),
                max_minutes=session_cfg.get("max_minutes", 60.0),
                max_tokens_total=session_cfg.get("max_tokens_total", 100000),
                max_turns_per_agent=session_cfg.get("max_turns_per_agent"),
                cooldown_seconds=session_cfg.get("cooldown_seconds", 0.0),
            )

            self.session_cfg = session_cfg
            self.agents_cfg = agents_cfg

            # Write log header
            debug.debug("Writing session log header")
            self._write_log_header()
            debug.info(f"Session initialized successfully: {self.session_id}")

        except Exception as e:
            debug.error(f"Failed to initialize session", exc=e)
            raise

    def _create_agents(self, agents_cfg: list[dict]) -> None:
        """Create agent instances from config.

        Args:
            agents_cfg: List of agent configs

        Raises:
            ValueError: If provider is unknown or adapter creation fails
        """
        debug = get_debug_logger()
        adapters_map = {
            "openai": OpenAIAdapter,
            "google": GoogleAdapter,
            "anthropic": AnthropicAdapter,
        }

        for agent_cfg in agents_cfg:
            agent_id = agent_cfg["id"]
            provider = agent_cfg["provider"].lower()

            try:
                if provider not in adapters_map:
                    raise ValueError(f"Unknown provider '{provider}'. Supported: {', '.join(adapters_map.keys())}")

                debug.debug(f"Creating adapter for agent '{agent_id}': {provider}/{agent_cfg['model']}")
                adapter_class = adapters_map[provider]
                adapter = adapter_class(
                    api_key=agent_cfg["api_key"],
                    model=agent_cfg["model"],
                )

                agent = Agent(agent_cfg, adapter)
                self.agents[agent.id] = agent
                self.stats.record_agent_init(agent.id, agent.provider, agent.model)
                debug.debug(f"Agent '{agent_id}' created successfully")

            except Exception as e:
                debug.error(f"Failed to create agent '{agent_id}'", exc=e)
                raise ValueError(f"Failed to create agent '{agent_id}': {e}") from e

    def _write_log_header(self) -> None:
        """Write session header to log."""
        session_info = {
            "id": self.session_id,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        agents_info = []
        for agent in self.agents.values():
            agents_info.append({
                "id": agent.id,
                "role": agent.role,
                "provider": agent.provider,
                "model": agent.model,
                "attitude": agent.attitude,
            })

        self.logger.write_header(session_info, agents_info, self.session_cfg)
        self.logger.log_status(f"Session created with {len(self.agents)} agents")

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def get_all_agents(self) -> list[Agent]:
        """Get all agents in session.

        Returns:
            List of all Agent instances in arbitrary order
        """
        return list(self.agents.values())

    def get_status(self) -> dict:
        """Get current session status for logging/reporting.

        Returns:
            Dict with session_id, agent count, and guardrails status
        """
        return {
            "session_id": self.session_id,
            "num_agents": len(self.agents),
            "guardrails": self.guardrails.get_status(),
        }

    def __repr__(self) -> str:
        return f"Session({self.session_id}, {len(self.agents)} agents)"
