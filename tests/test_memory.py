"""Tests for agent memory."""

from src.memory import AgentMemory, Message


class TestAgentMemory:
    """Tests for AgentMemory."""

    def test_init(self):
        """Test memory initialization."""
        memory = AgentMemory("agent1", keep_last_messages=12, summarize_after_messages=24)
        assert memory.agent_id == "agent1"
        assert memory.keep_last_messages == 12
        assert memory.summarize_after_messages == 24
        assert len(memory.raw_messages) == 0

    def test_add_message(self):
        """Test adding messages."""
        memory = AgentMemory("agent1")
        memory.add_message("user", "Hello", turn=0)
        memory.add_message("assistant", "Hi there", turn=1)

        assert len(memory.raw_messages) == 2
        assert memory.raw_messages[0].role == "user"
        assert memory.raw_messages[0].content == "Hello"
        assert memory.raw_messages[1].role == "assistant"
        assert memory.total_turns == 1

    def test_get_context_messages(self):
        """Test building context for LLM call."""
        memory = AgentMemory("agent1")
        memory.add_message("user", "Hello", turn=0)
        memory.add_message("assistant", "Hi", turn=1)

        context = memory.get_context_messages()
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"

    def test_context_includes_summary(self):
        """Test that summary is included in context."""
        memory = AgentMemory("agent1")
        memory.rolling_summary = "Earlier we talked about X"
        memory.add_message("user", "And now Y", turn=5)

        context = memory.get_context_messages()
        assert len(context) == 2
        assert context[0]["role"] == "system"
        assert "Summary" in context[0]["content"]
        assert context[1]["role"] == "user"

    def test_needs_summary(self):
        """Test summarization threshold."""
        memory = AgentMemory("agent1", summarize_after_messages=5)

        # Add messages below threshold
        for i in range(4):
            memory.add_message("user", f"Message {i}", turn=i)
        assert not memory.needs_summary()

        # Cross threshold
        memory.add_message("user", "Message 4", turn=4)
        assert memory.needs_summary()

    def test_update_summary(self):
        """Test updating summary and pruning old messages."""
        memory = AgentMemory("agent1", keep_last_messages=3)

        # Add 10 messages
        for i in range(10):
            memory.add_message("user", f"Message {i}", turn=i)

        assert len(memory.raw_messages) == 10

        # Update summary and prune
        memory.update_summary("Summary of first 7 messages")
        assert memory.rolling_summary == "Summary of first 7 messages"
        assert len(memory.raw_messages) <= memory.keep_last_messages

    def test_get_token_estimate(self):
        """Test token estimation."""
        memory = AgentMemory("agent1")
        memory.add_message("user", "a" * 100, turn=0)

        estimate = memory.get_token_estimate()
        assert estimate >= 20  # Rough estimate

    def test_window_size_limit(self):
        """Test that context is limited to window size."""
        memory = AgentMemory("agent1", keep_last_messages=3)

        # Add 10 messages
        for i in range(10):
            memory.add_message("user", f"Message {i}", turn=i)

        # Context should only include last 3 raw messages
        context = memory.get_context_messages()
        assert len(context) == 3
        assert "Message 7" in context[0]["content"]
        assert "Message 8" in context[1]["content"]
        assert "Message 9" in context[2]["content"]

    def test_empty_memory_context(self):
        """Test context from empty memory."""
        memory = AgentMemory("agent1")
        context = memory.get_context_messages()
        assert len(context) == 0

    def test_repr(self):
        """Test string representation."""
        memory = AgentMemory("agent1")
        memory.add_message("user", "Hello", turn=0)
        assert "agent1" in repr(memory)
        assert "1" in repr(memory)  # One raw message
