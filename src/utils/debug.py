"""Debug logging for internal actions and troubleshooting."""

import logging
import sys
from pathlib import Path


class DebugLogger:
    """Structured debug logging for internal operations."""

    def __init__(self, debug_file: str = "./logs/debug.log", level: int = logging.INFO):
        """Initialize debug logger.

        Args:
            debug_file: Path to debug log file
            level: Logging level (INFO, DEBUG, WARNING, ERROR)
        """
        self.debug_file = Path(debug_file)
        self.debug_file.parent.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger("lan_llm_hub_debug")
        self.logger.setLevel(level)

        # File handler
        try:
            file_handler = logging.FileHandler(self.debug_file, mode="a")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except IOError as e:
            print(f"WARNING: Could not create debug log file: {e}", flush=True)

        # Console handler (stderr for errors)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter("[DEBUG] %(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc: Exception = None) -> None:
        """Log error message with optional exception details."""
        if exc:
            self.logger.error(f"{message} | Exception: {type(exc).__name__}: {exc}")
        else:
            self.logger.error(message)


# Global debug logger instance
_debug_logger = None


def get_debug_logger(debug_file: str = "./logs/debug.log") -> DebugLogger:
    """Get or create global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger(debug_file=debug_file)
    return _debug_logger
