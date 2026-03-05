"""Session logging (human-readable and machine-readable formats)."""

import json
import os
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """Logs session events in human-readable and optional JSONL formats."""

    def __init__(self, session_id: str, log_dir: str = "./logs", enable_jsonl: bool = True):
        """Initialize logger.

        Args:
            session_id: Session ID (usually YYYYMMDDhhmmss)
            log_dir: Directory for log files
            enable_jsonl: Whether to write machine-readable JSONL events log
        """
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.enable_jsonl = enable_jsonl

        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Log file paths
        self.log_file = self.log_dir / f"{session_id}.log"
        self.jsonl_file = self.log_dir / f"{session_id}.events.jsonl" if enable_jsonl else None

    def write_header(self, session_info: dict, agents_info: list[dict], config: dict) -> None:
        """Write session header with metadata.

        Args:
            session_info: Dict with 'id', 'start_time', etc.
            agents_info: List of agent configs
            config: Session config
        """
        lines = [
            "=" * 80,
            f"LAN-LLM-Hub Session Log",
            f"Session ID: {session_info.get('id')}",
            f"Start Time: {session_info.get('start_time')}",
            "=" * 80,
            "",
            "AGENTS:",
        ]

        for agent in agents_info:
            lines.append(
                f"  {agent['id']}: {agent['provider']}/{agent['model']} "
                f"(role={agent.get('role', 'participant')})"
            )
            if agent.get("attitude"):
                lines.append(f"    Attitude: {agent['attitude']}")

        lines.extend([
            "",
            "SESSION CONFIG:",
            f"  Topology: {config.get('topology')}",
            f"  Max Turns: {config.get('max_turns_total')}",
            f"  Max Time: {config.get('max_minutes')} minutes",
            f"  Max Tokens: {config.get('max_tokens_total')}",
            f"  Memory Window: {config.get('keep_last_messages')} messages",
            "",
            "=" * 80,
            "",
        ])

        self._write_to_file(self.log_file, "\n".join(lines))

    def log_event(
        self,
        sender: str,
        content: str,
        event_type: str = "message",
        metadata: dict = None,
    ) -> None:
        """Log a message or event.

        Args:
            sender: Agent ID or 'ADMIN'
            content: Event content/message text
            event_type: 'message', 'error', 'status', 'session_end'
            metadata: Optional metadata (usage, latency, etc.)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp}: [{sender}] {content}\n"
        self._write_to_file(self.log_file, line, append=True)

        # Also write to JSONL if enabled
        if self.enable_jsonl and self.jsonl_file:
            event = {
                "timestamp": timestamp,
                "sender": sender,
                "event_type": event_type,
                "content": content,
            }
            if metadata:
                event.update(metadata)

            jsonl_line = json.dumps(event) + "\n"
            self._write_to_file(self.jsonl_file, jsonl_line, append=True)

    def log_error(self, error_msg: str, agent_id: str = "HUB") -> None:
        """Log an error.

        Args:
            error_msg: Error message
            agent_id: Agent that caused error (default 'HUB')
        """
        self.log_event(agent_id, f"ERROR: {error_msg}", event_type="error")

    def log_status(self, status_msg: str) -> None:
        """Log a status message.

        Args:
            status_msg: Status message
        """
        self.log_event("HUB", status_msg, event_type="status")

    def log_session_end(self, reason: str, stats: dict) -> None:
        """Log session end.

        Args:
            reason: Reason for ending
            stats: Final stats (turns, tokens, etc.)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "",
            "=" * 80,
            f"SESSION END: {reason}",
            f"End Time: {timestamp}",
            "Final Stats:",
        ]
        for key, value in stats.items():
            lines.append(f"  {key}: {value}")
        lines.append("=" * 80)

        self._write_to_file(self.log_file, "\n".join(lines), append=True)

    def _write_to_file(self, filepath: Path, content: str, append: bool = False) -> None:
        """Write content to file.

        Args:
            filepath: Path to file
            content: Content to write
            append: If True, append; if False, write (overwrite)
        """
        mode = "a" if append else "w"
        try:
            with open(filepath, mode) as f:
                f.write(content)
        except IOError as e:
            print(f"ERROR writing to {filepath}: {e}", flush=True)

    def get_log_file(self) -> str:
        """Get path to human-readable log file."""
        return str(self.log_file)

    def get_jsonl_file(self) -> str:
        """Get path to JSONL events file."""
        return str(self.jsonl_file) if self.jsonl_file else None
