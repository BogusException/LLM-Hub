"""Tests for message router."""

from src.router import Router, TopologyType


class TestRouterHubSpoke:
    """Tests for hub-spoke topology."""

    def test_hub_spoke_broadcast_except_sender(self):
        """Test hub-spoke with broadcast_except_sender."""
        agents = ["agent1", "agent2", "agent3"]
        router = Router(
            topology=TopologyType.HUB_SPOKE,
            agents=agents,
            fanout="broadcast_except_sender",
        )

        # agent1 sends, agent2 and agent3 receive
        recipients = router.get_recipients("agent1")
        assert set(recipients) == {"agent2", "agent3"}

        # agent2 sends, agent1 and agent3 receive
        recipients = router.get_recipients("agent2")
        assert set(recipients) == {"agent1", "agent3"}

    def test_hub_spoke_broadcast_all(self):
        """Test hub-spoke with broadcast_all."""
        agents = ["agent1", "agent2", "agent3"]
        router = Router(
            topology=TopologyType.HUB_SPOKE,
            agents=agents,
            fanout="broadcast_all",
        )

        recipients = router.get_recipients("agent1")
        assert set(recipients) == set(agents)

    def test_hub_spoke_limited_1(self):
        """Test hub-spoke with limited_1 fanout."""
        agents = ["agent1", "agent2", "agent3"]
        router = Router(
            topology=TopologyType.HUB_SPOKE,
            agents=agents,
            fanout="limited_1",
        )

        recipients = router.get_recipients("agent1")
        assert len(recipients) <= 1
        assert "agent1" not in recipients


class TestRouterStar:
    """Tests for star topology."""

    def test_star_actor_sends_to_interrogators(self):
        """Test actor sends to all interrogators."""
        agents = ["actor", "interrog1", "interrog2"]
        router = Router(
            topology=TopologyType.STAR,
            agents=agents,
            star_actor="actor",
        )

        recipients = router.get_recipients("actor")
        assert set(recipients) == {"interrog1", "interrog2"}

    def test_star_interrogator_sends_to_actor(self):
        """Test interrogator sends to actor only."""
        agents = ["actor", "interrog1", "interrog2"]
        router = Router(
            topology=TopologyType.STAR,
            agents=agents,
            star_actor="actor",
        )

        recipients = router.get_recipients("interrog1")
        assert recipients == ["actor"]

    def test_star_private_message(self):
        """Test private messages in star topology."""
        agents = ["actor", "interrog1", "judge"]
        router = Router(
            topology=TopologyType.STAR,
            agents=agents,
            star_actor="actor",
        )

        # Private message from interrogator
        recipients = router.get_recipients("interrog1", message_type="private")
        assert recipients == []  # Private messages handled separately


class TestRouterRoundRobin:
    """Tests for round-robin topology."""

    def test_round_robin_rotates(self):
        """Test round-robin rotates through agents."""
        agents = ["agent1", "agent2", "agent3"]
        router = Router(
            topology=TopologyType.ROUND_ROBIN,
            agents=agents,
        )

        # Round-robin should return next speaker each time
        speakers = []
        for _ in range(6):
            speakers.append(router.get_recipients("dummy")[0])

        # Should cycle through agents in order
        assert speakers[0] == agents[1]  # Start at index 1
        assert speakers[1] == agents[2]
        assert speakers[2] == agents[0]
        assert speakers[3] == agents[1]


class TestRouterMesh:
    """Tests for mesh topology."""

    def test_mesh_everyone_talks_to_everyone(self):
        """Test mesh topology (all-to-all)."""
        agents = ["agent1", "agent2", "agent3"]
        router = Router(
            topology=TopologyType.MESH,
            agents=agents,
        )

        recipients = router.get_recipients("agent1")
        assert set(recipients) == {"agent2", "agent3"}


class TestRouterArbiterGated:
    """Tests for arbiter-gated topology."""

    def test_arbiter_can_send_to_anyone(self):
        """Test arbiter can send to any agent."""
        agents = ["arbiter", "agent1", "agent2"]
        router = Router(
            topology=TopologyType.ARBITER_GATED,
            agents=agents,
            arbiter="arbiter",
        )

        recipients = router.get_recipients("arbiter")
        assert set(recipients) == {"agent1", "agent2"}

    def test_non_arbiter_sends_to_arbiter_only(self):
        """Test non-arbiter agents send to arbiter only."""
        agents = ["arbiter", "agent1", "agent2"]
        router = Router(
            topology=TopologyType.ARBITER_GATED,
            agents=agents,
            arbiter="arbiter",
        )

        recipients = router.get_recipients("agent1")
        assert recipients == ["arbiter"]
