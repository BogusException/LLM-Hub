"""Guardrails: stop conditions, budgets, and loop detection."""

import time
from collections import defaultdict
from hashlib import md5
from typing import Optional


class Guardrails:
    """Enforce budget limits and detect loops."""

    def __init__(
        self,
        max_turns_total: int = 100,
        max_minutes: float = 60.0,
        max_tokens_total: int = 100000,
        max_turns_per_agent: Optional[int] = None,
        cooldown_seconds: float = 0.0,
        duplicate_threshold: int = 3,
    ):
        """Initialize guardrails.

        Args:
            max_turns_total: Maximum total turns for session
            max_minutes: Maximum minutes for session
            max_tokens_total: Maximum total tokens for session
            max_turns_per_agent: Max turns per agent (None = unlimited)
            cooldown_seconds: Minimum seconds between agent calls
            duplicate_threshold: Mute agent after N consecutive duplicate messages
        """
        self.max_turns_total = max_turns_total
        self.max_minutes = max_minutes
        self.max_tokens_total = max_tokens_total
        self.max_turns_per_agent = max_turns_per_agent
        self.cooldown_seconds = cooldown_seconds

        # Session tracking
        self.session_start_time = time.time()
        self.current_turn = 0
        self.total_tokens_used = 0
        self.agent_turns = defaultdict(int)
        self.agent_last_call_time = defaultdict(float)

        # Loop detection
        self.recent_messages = []  # (agent_id, message_hash)
        self.message_history_window = 10  # Keep last N messages for dedup
        self.duplicate_threshold = duplicate_threshold  # Mute agent after N duplicates

    def check_session_limits(self) -> tuple[bool, str]:
        """Check if session should continue.

        Returns:
            (should_continue, reason_if_stopped)
        """
        elapsed_minutes = (time.time() - self.session_start_time) / 60.0

        if self.current_turn >= self.max_turns_total:
            return False, f"Reached max turns ({self.max_turns_total})"

        if elapsed_minutes >= self.max_minutes:
            return False, f"Reached max time ({self.max_minutes} min)"

        if self.total_tokens_used >= self.max_tokens_total:
            return False, f"Reached max tokens ({self.max_tokens_total})"

        return True, ""

    def check_agent_limits(self, agent_id: str) -> tuple[bool, str]:
        """Check if agent can speak.

        Returns:
            (can_speak, reason_if_cannot)
        """
        if self.max_turns_per_agent and self.agent_turns[agent_id] >= self.max_turns_per_agent:
            return False, f"Agent {agent_id} reached max turns"

        # Check cooldown
        last_call = self.agent_last_call_time.get(agent_id, 0)
        elapsed = time.time() - last_call
        if elapsed < self.cooldown_seconds:
            return False, f"Agent {agent_id} in cooldown ({self.cooldown_seconds}s)"

        return True, ""

    def record_agent_call(self, agent_id: str, input_tokens: int, output_tokens: int) -> None:
        """Record that an agent made a call.

        Args:
            agent_id: Agent that called
            input_tokens: Tokens used in input
            output_tokens: Tokens used in output
        """
        self.agent_turns[agent_id] += 1
        self.agent_last_call_time[agent_id] = time.time()
        self.total_tokens_used += input_tokens + output_tokens

    def record_message(self, agent_id: str, message: str) -> None:
        """Record a message for loop detection.

        Args:
            agent_id: Agent that produced message
            message: Message text
        """
        msg_hash = md5(message.encode()).hexdigest()
        self.recent_messages.append((agent_id, msg_hash))

        # Keep only recent messages
        if len(self.recent_messages) > self.message_history_window:
            self.recent_messages = self.recent_messages[-self.message_history_window:]

    def check_for_loops(self) -> tuple[bool, Optional[str]]:
        """Check if any agent is looping (repeating itself).

        Algorithm: Scan through recent messages in reverse order. For each agent,
        count consecutive identical messages (by MD5 hash). If any agent has produced
        N consecutive identical messages (where N >= duplicate_threshold), that agent
        is considered to be looping.

        This catches agents that are stuck in a pattern of repeating the same response.

        Returns:
            (is_looping, looping_agent_id_or_none)
        """
        # Count message frequency per agent (simple metric, not used for detection)
        agent_duplicates = defaultdict(int)
        for agent_id, msg_hash in self.recent_messages:
            agent_duplicates[agent_id] += 1

        # Find agents with consecutive duplicate messages
        for agent_id, count in agent_duplicates.items():
            # Scan recent messages in reverse (most recent first)
            consecutive = 0
            last_hash = None
            for a, h in reversed(self.recent_messages):
                if a == agent_id:
                    if h == last_hash:
                        consecutive += 1
                    else:
                        consecutive = 1
                    last_hash = h
                    # If this agent has produced duplicate_threshold consecutive identical messages
                    if consecutive >= self.duplicate_threshold:
                        return True, agent_id

        return False, None

    def check_convergence(self) -> bool:
        """Check if conversation shows low novelty (simple heuristic).

        Algorithm: Look at the last 5 messages. If fewer than 2 unique message
        hashes are seen (i.e., agents are repeating similar content), the conversation
        has likely converged (no new information being added).

        This is a simple heuristic and may flag legitimate scenarios (e.g., agents
        reaching consensus) as convergence. Future versions should use semantic
        similarity or task-specific metrics.

        Returns:
            True if conversation appears to have converged (low novelty)
        """
        if len(self.recent_messages) < 5:
            return False

        # Count unique hashes in the last 5 messages
        unique_hashes = len(set(h for _, h in self.recent_messages[-5:]))

        # If less than 2 unique messages in last 5, probably converged
        # (threshold of 2 means either 1 repeated message or 2 agents alternating)
        return unique_hashes < 2

    def advance_turn(self) -> None:
        """Advance to next turn."""
        self.current_turn += 1

    def get_status(self) -> dict:
        """Get current status for logging.

        Returns:
            Dict with session status info
        """
        elapsed_minutes = (time.time() - self.session_start_time) / 60.0
        return {
            "turn": self.current_turn,
            "elapsed_minutes": round(elapsed_minutes, 2),
            "total_tokens": self.total_tokens_used,
            "agents_active": dict(self.agent_turns),
        }
