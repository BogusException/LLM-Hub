"""Statistics collection and analysis for LAN-LLM-Hub sessions."""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class StatsCollector:
    """Collect metrics about session execution for analysis."""

    def __init__(self, session_id: str, log_dir: str = "./logs"):
        """Initialize stats collector for a session.

        Args:
            session_id: Unique session identifier
            log_dir: Directory where stats will be written
        """
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.end_reason: Optional[str] = None

        # Agent metrics (per agent)
        self.agent_metrics: dict[str, dict] = {}

        # Conversation metrics
        self.total_turns = 0
        self.total_messages = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0

        # Routing metrics
        self.routing_events: list[dict] = []

        # Memory events
        self.memory_events: list[dict] = []

        # Events log (for detailed analysis)
        self.events: list[dict] = []

    def record_agent_init(self, agent_id: str, provider: str, model: str) -> None:
        """Record agent initialization.

        Args:
            agent_id: Agent identifier
            provider: LLM provider (openai, anthropic, google)
            model: Model name
        """
        self.agent_metrics[agent_id] = {
            "provider": provider,
            "model": model,
            "messages_sent": 0,
            "messages_received": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "latencies_ms": [],
            "errors": 0,
        }

    def record_agent_call(
        self,
        agent_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Record an LLM API call for an agent.

        Args:
            agent_id: Agent making the call
            tokens_in: Input tokens consumed
            tokens_out: Output tokens produced
            latency_ms: API response time in milliseconds
            error: Error message if call failed
        """
        if agent_id not in self.agent_metrics:
            self.record_agent_init(agent_id, "unknown", "unknown")

        metrics = self.agent_metrics[agent_id]
        metrics["messages_sent"] += 1
        metrics["tokens_in"] += tokens_in
        metrics["tokens_out"] += tokens_out
        metrics["latencies_ms"].append(latency_ms)

        if error:
            metrics["errors"] += 1

        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_messages += 1

        self.events.append({
            "type": "agent_call",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "error": error,
        })

    def record_message_received(self, agent_id: str) -> None:
        """Record that an agent received a message.

        Args:
            agent_id: Agent receiving the message
        """
        if agent_id not in self.agent_metrics:
            self.record_agent_init(agent_id, "unknown", "unknown")

        self.agent_metrics[agent_id]["messages_received"] += 1

    def record_routing(self, sender_id: str, recipients: list[str]) -> None:
        """Record a routing decision.

        Args:
            sender_id: Agent sending the message
            recipients: List of agent IDs receiving the message
        """
        self.routing_events.append({
            "timestamp": datetime.now().isoformat(),
            "sender": sender_id,
            "recipient_count": len(recipients),
            "recipients": recipients,
        })

    def record_memory_event(self, agent_id: str, event_type: str, detail: str) -> None:
        """Record a memory management event (summarization, etc.).

        Args:
            agent_id: Agent whose memory changed
            event_type: Type of event (summarization, etc.)
            detail: Details about the event
        """
        self.memory_events.append({
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "event_type": event_type,
            "detail": detail,
        })

    def record_turn_advance(self) -> None:
        """Record that a turn has been completed."""
        self.total_turns += 1

    def record_session_end(self, reason: str) -> None:
        """Record session termination.

        Args:
            reason: Why the session ended (convergence, max_turns, etc.)
        """
        self.end_time = datetime.now()
        self.end_reason = reason

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics for the session.

        Returns:
            Dictionary with summary stats
        """
        elapsed = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time
            else (datetime.now() - self.start_time).total_seconds()
        )

        # Agent-level summaries
        agent_summaries = {}
        for agent_id, metrics in self.agent_metrics.items():
            latencies = metrics["latencies_ms"]
            agent_summaries[agent_id] = {
                "provider": metrics["provider"],
                "model": metrics["model"],
                "messages_sent": metrics["messages_sent"],
                "messages_received": metrics["messages_received"],
                "tokens_in": metrics["tokens_in"],
                "tokens_out": metrics["tokens_out"],
                "total_tokens": metrics["tokens_in"] + metrics["tokens_out"],
                "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
                "min_latency_ms": round(min(latencies), 1) if latencies else 0,
                "max_latency_ms": round(max(latencies), 1) if latencies else 0,
                "errors": metrics["errors"],
            }

        # Routing summary
        avg_recipients = (
            sum(e["recipient_count"] for e in self.routing_events) / len(self.routing_events)
            if self.routing_events
            else 0
        )

        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": round(elapsed, 1),
            "end_reason": self.end_reason,
            "summary": {
                "total_turns": self.total_turns,
                "total_messages": self.total_messages,
                "total_tokens_in": self.total_tokens_in,
                "total_tokens_out": self.total_tokens_out,
                "total_tokens": self.total_tokens_in + self.total_tokens_out,
                "avg_tokens_per_turn": round(
                    (self.total_tokens_in + self.total_tokens_out) / max(1, self.total_turns),
                    1,
                ),
            },
            "agents": agent_summaries,
            "routing": {
                "total_routing_events": len(self.routing_events),
                "avg_recipients_per_message": round(avg_recipients, 1),
            },
            "memory": {
                "summarization_events": len(self.memory_events),
                "memory_events": self.memory_events,
            },
        }

    def write_stats(self) -> Path:
        """Write stats to JSON file.

        Returns:
            Path to written stats file
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stats_file = self.log_dir / f"{self.session_id}.stats.json"

        stats_data = self.get_summary()

        with open(stats_file, "w") as f:
            json.dump(stats_data, f, indent=2)

        return stats_file
