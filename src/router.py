"""Message router based on configurable topologies."""

from enum import Enum
from typing import Optional


class TopologyType(Enum):
    """Available routing topologies."""
    HUB_SPOKE = "hub_spoke"
    STAR = "star"
    ROUND_ROBIN = "round_robin"
    MESH = "mesh"
    ARBITER_GATED = "arbiter_gated"


class Router:
    """Routes messages between agents based on topology."""

    def __init__(
        self,
        topology: TopologyType,
        agents: list[str],
        fanout: str = "broadcast_except_sender",
        star_actor: Optional[str] = None,
        arbiter: Optional[str] = None,
    ):
        """Initialize router with topology and agent list.

        Args:
            topology: TopologyType (hub_spoke, star, round_robin, mesh, arbiter_gated)
            agents: List of agent IDs
            fanout: Fanout strategy ('broadcast_except_sender', 'broadcast_all', 'limited_1', 'limited_2')
            star_actor: Agent ID of the actor (for 'star' topology)
            arbiter: Agent ID of the arbiter (for 'arbiter_gated' topology)
        """
        self.topology = topology
        self.agents = agents
        self.fanout = fanout
        self.star_actor = star_actor
        self.arbiter = arbiter
        self.round_robin_index = 0

    def get_recipients(self, sender: str, message_type: str = "public") -> list[str]:
        """Determine which agents should receive a message based on topology.

        This is the main routing decision point. The topology determines how messages
        flow between agents. See LAN-LLM-Hub.md for detailed topology descriptions.

        Args:
            sender: Agent ID sending the message
            message_type: 'public' or 'private'

        Returns:
            List of agent IDs that should receive the message
        """
        if self.topology == TopologyType.HUB_SPOKE:
            return self._hub_spoke_recipients(sender)
        elif self.topology == TopologyType.STAR:
            return self._star_recipients(sender, message_type)
        elif self.topology == TopologyType.ROUND_ROBIN:
            return self._round_robin_recipients()
        elif self.topology == TopologyType.MESH:
            return self._mesh_recipients(sender)
        elif self.topology == TopologyType.ARBITER_GATED:
            return self._arbiter_gated_recipients(sender, message_type)
        else:
            return []

    def _hub_spoke_recipients(self, sender: str) -> list[str]:
        """Hub-spoke topology: Sender broadcasts to multiple agents (fanout-controlled).

        In hub-spoke, one agent sends, and the hub decides how many/which agents
        receive the message based on fanout strategy:
        - broadcast_except_sender: all agents except sender
        - broadcast_all: all agents including sender (unusual)
        - limited_1: only next agent
        - limited_2: next two agents (reduces n² explosion)

        Args:
            sender: Agent ID sending the message

        Returns:
            List of recipient agent IDs
        """
        if self.fanout == "broadcast_except_sender":
            return [a for a in self.agents if a != sender]
        elif self.fanout == "broadcast_all":
            return self.agents
        elif self.fanout == "limited_1":
            others = [a for a in self.agents if a != sender]
            return others[:1] if others else []
        elif self.fanout == "limited_2":
            others = [a for a in self.agents if a != sender]
            return others[:2] if others else []
        else:
            return [a for a in self.agents if a != sender]

    def _star_recipients(self, sender: str, message_type: str) -> list[str]:
        """Star topology: One actor talks to many interrogators.

        Used for scenarios like Turing tests or interrogation harnesses.
        - Actor (central agent): sends to all interrogators
        - Interrogators: send public messages only to actor
        - Interrogators: send private messages to judge (handled separately)

        This topology prevents interrogators from talking to each other (reduces chaos),
        while keeping actor visible to all.

        Args:
            sender: Agent ID sending the message
            message_type: 'public' or 'private'

        Returns:
            List of recipient agent IDs
        """
        if sender == self.star_actor:
            # Actor talks to all non-actor agents (interrogators)
            return [a for a in self.agents if a != self.star_actor]
        else:
            # Interrogator talks to actor only
            if message_type == "private":
                # Private messages from interrogators handled separately by session
                return []
            else:
                return [self.star_actor] if self.star_actor in self.agents else []

    def _round_robin_recipients(self) -> list[str]:
        """Round-robin: rotate speaker each turn."""
        if not self.agents:
            return []
        # Next speaker is determined by external session logic
        # Router just provides the next index
        self.round_robin_index = (self.round_robin_index + 1) % len(self.agents)
        return [self.agents[self.round_robin_index]]

    def _mesh_recipients(self, sender: str) -> list[str]:
        """Mesh: everyone talks to everyone."""
        return [a for a in self.agents if a != sender]

    def _arbiter_gated_recipients(self, sender: str, message_type: str) -> list[str]:
        """Arbiter-gated: only arbiter can forward messages.

        Messages go to arbiter; arbiter decides recipients.
        This is typically enforced by session logic, not here.
        """
        if sender == self.arbiter:
            # Arbiter can send to anyone
            return [a for a in self.agents if a != self.arbiter]
        else:
            # Non-arbiter sends to arbiter only
            return [self.arbiter] if self.arbiter in self.agents else []

    def __repr__(self) -> str:
        return f"Router({self.topology.value}, agents={len(self.agents)})"
