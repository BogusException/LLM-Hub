"""Per-agent bounded memory with window + rolling summary pattern."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """A single message in memory."""
    role: str  # 'system', 'user', 'assistant'
    content: str
    turn: int  # Turn number when this message was created


@dataclass
class AgentMemory:
    """Bounded memory buffer for a single agent."""
    agent_id: str
    keep_last_messages: int = 12  # Keep last N messages verbatim
    summarize_after_messages: int = 24  # Summarize after N messages

    raw_messages: list[Message] = field(default_factory=list)
    rolling_summary: str = ""
    total_turns: int = 0

    def add_message(self, role: str, content: str, turn: int) -> None:
        """Add a message to memory.

        Args:
            role: Message role ('system', 'user', 'assistant')
            content: Message text
            turn: Turn number when this message was created
        """
        msg = Message(role=role, content=content, turn=turn)
        self.raw_messages.append(msg)
        self.total_turns = max(self.total_turns, turn)

    def get_context_messages(self) -> list[dict]:
        """Build context messages for LLM call.

        This implements the window + rolling summary pattern:
        - If there's a rolling summary (from older messages), include it first
        - Then include only the last N raw messages verbatim

        This keeps context bounded while maintaining continuity. A 100-message
        conversation becomes: summary_of_first_80 + last_12_messages = ~20 messages.

        Returns:
            List of message dicts in OpenAI format: [{'role': '...', 'content': '...'}]
            Structure: [summary (if exists), ...last N raw messages]
        """
        context = []

        # Add rolling summary if it exists (gives agent context on older conversation)
        if self.rolling_summary:
            context.append({
                "role": "system",
                "content": f"[Summary of earlier conversation]\n{self.rolling_summary}"
            })

        # Add only the last N raw messages (keep conversation recent and bounded)
        for msg in self.raw_messages[-self.keep_last_messages:]:
            context.append({
                "role": msg.role,
                "content": msg.content,
            })

        return context

    def update_summary(self, new_summary: str) -> None:
        """Update rolling summary and prune old raw messages.

        When summarization happens, replace detailed messages with a summary,
        then keep only the most recent raw messages. This prevents memory
        from growing unbounded while maintaining conversation context.

        Example: If summary_after=24 and keep_last=12, after summarization
        we'll have ~summary + 12 recent messages instead of 24+ raw messages.

        Args:
            new_summary: New summary text (typically output from a summarizer agent)
        """
        self.rolling_summary = new_summary
        # Prune old raw messages, keep only recent ones
        if len(self.raw_messages) > self.keep_last_messages:
            self.raw_messages = self.raw_messages[-self.keep_last_messages:]

    def needs_summary(self) -> bool:
        """Check if memory should be summarized.

        Returns:
            True if raw messages exceed the summarize_after_messages threshold.
            The main loop should check this and call a summarizer agent if True.
        """
        return len(self.raw_messages) >= self.summarize_after_messages

    def get_token_estimate(self) -> int:
        """Rough token estimate for all messages.

        Returns:
            Estimated token count (4 chars ≈ 1 token)
        """
        total_chars = sum(len(msg.content) for msg in self.raw_messages)
        summary_chars = len(self.rolling_summary)
        return (total_chars + summary_chars) // 4

    def __repr__(self) -> str:
        return (
            f"AgentMemory({self.agent_id}, "
            f"raw_msgs={len(self.raw_messages)}, "
            f"turns={self.total_turns})"
        )
