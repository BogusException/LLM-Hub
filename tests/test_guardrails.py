"""Tests for guardrails and stop conditions."""

import time
from src.guardrails import Guardrails


class TestGuardrailsBasic:
    """Tests for basic guardrail checks."""

    def test_init(self):
        """Test guardrails initialization."""
        gr = Guardrails(
            max_turns_total=100,
            max_minutes=60.0,
            max_tokens_total=100000,
        )
        assert gr.max_turns_total == 100
        assert gr.current_turn == 0
        assert gr.total_tokens_used == 0

    def test_check_session_limits_ok(self):
        """Test session limits when not exceeded."""
        gr = Guardrails(max_turns_total=100, max_minutes=60.0)
        should_continue, reason = gr.check_session_limits()
        assert should_continue is True

    def test_check_max_turns(self):
        """Test max turns limit."""
        gr = Guardrails(max_turns_total=5)
        for i in range(6):
            gr.advance_turn()

        should_continue, reason = gr.check_session_limits()
        assert should_continue is False
        assert "max turns" in reason.lower()

    def test_check_max_tokens(self):
        """Test max tokens limit."""
        gr = Guardrails(max_tokens_total=100)
        gr.total_tokens_used = 150
        should_continue, reason = gr.check_session_limits()
        assert should_continue is False
        assert "tokens" in reason.lower()

    def test_agent_limits_ok(self):
        """Test agent limits when not exceeded."""
        gr = Guardrails(max_turns_per_agent=10)
        can_speak, reason = gr.check_agent_limits("agent1")
        assert can_speak is True

    def test_agent_max_turns_exceeded(self):
        """Test agent exceeding max turns."""
        gr = Guardrails(max_turns_per_agent=3)
        for i in range(4):
            gr.agent_turns["agent1"] = i + 1

        can_speak, reason = gr.check_agent_limits("agent1")
        assert can_speak is False
        assert "agent1" in reason

    def test_agent_cooldown(self):
        """Test agent cooldown."""
        gr = Guardrails(cooldown_seconds=1.0)
        gr.agent_last_call_time["agent1"] = time.time()

        can_speak, reason = gr.check_agent_limits("agent1")
        assert can_speak is False
        assert "cooldown" in reason.lower()

    def test_agent_cooldown_expires(self):
        """Test cooldown expires."""
        gr = Guardrails(cooldown_seconds=0.1)
        gr.agent_last_call_time["agent1"] = time.time() - 0.2
        can_speak, reason = gr.check_agent_limits("agent1")
        assert can_speak is True


class TestGuardrailsRecording:
    """Tests for recording events."""

    def test_record_agent_call(self):
        """Test recording an agent call."""
        gr = Guardrails()
        gr.record_agent_call("agent1", input_tokens=10, output_tokens=5)

        assert gr.agent_turns["agent1"] == 1
        assert gr.total_tokens_used == 15
        assert gr.agent_last_call_time["agent1"] > 0

    def test_record_message(self):
        """Test recording a message."""
        gr = Guardrails()
        gr.record_message("agent1", "Hello world")

        assert len(gr.recent_messages) == 1
        assert gr.recent_messages[0][0] == "agent1"

    def test_record_message_window(self):
        """Test message history window limit."""
        gr = Guardrails()
        for i in range(15):
            gr.record_message("agent1", f"Message {i}")

        # Should keep only last 10
        assert len(gr.recent_messages) == gr.message_history_window


class TestGuardrailsLoopDetection:
    """Tests for loop detection."""

    def test_no_loop_different_messages(self):
        """Test no loop with different messages."""
        gr = Guardrails()
        gr.record_message("agent1", "Message 1")
        gr.record_message("agent1", "Message 2")
        gr.record_message("agent1", "Message 3")

        is_looping, looping_agent = gr.check_for_loops()
        assert is_looping is False

    def test_detect_agent_repeating(self):
        """Test detecting agent repeating same message."""
        gr = Guardrails(duplicate_threshold=2)
        # Agent repeats same message
        gr.record_message("agent1", "Same message")
        gr.record_message("agent1", "Same message")
        gr.record_message("agent1", "Same message")

        is_looping, looping_agent = gr.check_for_loops()
        assert is_looping is True
        assert looping_agent == "agent1"

    def test_no_loop_interspersed(self):
        """Test no loop when messages are interspersed."""
        gr = Guardrails(duplicate_threshold=3)
        gr.record_message("agent1", "A")
        gr.record_message("agent2", "B")
        gr.record_message("agent1", "A")

        is_looping, looping_agent = gr.check_for_loops()
        assert is_looping is False


class TestGuardrailsConvergence:
    """Tests for convergence detection."""

    def test_convergence_low_novelty(self):
        """Test convergence with low novelty."""
        gr = Guardrails()
        gr.record_message("agent1", "Same message")
        gr.record_message("agent2", "Same message")
        gr.record_message("agent1", "Same message")
        gr.record_message("agent2", "Same message")
        gr.record_message("agent1", "Same message")

        is_converged = gr.check_convergence()
        assert is_converged is True

    def test_no_convergence_high_novelty(self):
        """Test no convergence with high novelty."""
        gr = Guardrails()
        gr.record_message("agent1", "Different message 1")
        gr.record_message("agent2", "Different message 2")
        gr.record_message("agent1", "Different message 3")
        gr.record_message("agent2", "Different message 4")
        gr.record_message("agent1", "Different message 5")

        is_converged = gr.check_convergence()
        assert is_converged is False

    def test_convergence_needs_minimum_messages(self):
        """Test convergence check needs minimum message count."""
        gr = Guardrails()
        gr.record_message("agent1", "Message")
        gr.record_message("agent1", "Message")

        is_converged = gr.check_convergence()
        assert is_converged is False  # Not enough messages


class TestGuardrailsStatus:
    """Tests for status reporting."""

    def test_get_status(self):
        """Test status dict."""
        gr = Guardrails()
        gr.advance_turn()
        gr.advance_turn()
        gr.agent_turns["agent1"] = 2
        gr.total_tokens_used = 500

        status = gr.get_status()
        assert status["turn"] == 2
        assert status["total_tokens"] == 500
        assert "agents_active" in status
        assert status["agents_active"]["agent1"] == 2
