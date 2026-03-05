# LAN-LLM-Hub

A configuration-driven multi-agent LLM orchestrator for LAN-hosted conversations between multiple providers (OpenAI, Anthropic, Google) and models.

## Overview

LAN-LLM-Hub coordinates conversations between multiple LLM agents across different providers. Different use cases—debate, consensus, interrogation, design review, and adversarial testing—are implemented as **configuration presets**, not separate systems. Same engine, different configuration.

**Key capabilities:**
- Route messages between agents in configurable topologies (hub-spoke, star, round-robin, mesh, arbiter-gated)
- Maintain bounded memory per agent to control token costs
- Enforce guardrails to prevent infinite loops and runaway budgets
- Support both public and private messages for evaluation scenarios
- Generate deterministic, tail-friendly logs for replay and debugging
- Run multiple instances of the same model with different personas

## Quick Links

- **[QUICKSTART.md](docs/QUICKSTART.md)** — Getting started from scratch (box to first run)
- **[GUIDE.md](docs/GUIDE.md)** — Complete architecture, topologies, use cases, and advanced configuration

## Common Use Cases

### Debate
Two or more agents with opposing views discuss a topic.

### Consensus / Design Review
Agents with different roles (analyst, designer, implementer) reach agreement on a solution.

### Interrogation Harness (Turing Test Style)
One "actor" agent tries to pass as human; interrogators score confidence privately; judge collects verdicts.

### Adversarial Testing
An agent tries to find flaws while another defends their reasoning.

## Installation

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config-template.toml config.toml
```

Edit `config.toml` with your API keys and agent definitions, then:

```bash
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
```

See **[QUICKSTART.md](docs/QUICKSTART.md)** for full details.

## Documentation Structure

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](docs/QUICKSTART.md) | Getting started in 5 minutes |
| [GUIDE.md](docs/GUIDE.md) | Routing topologies, memory management, guardrails, advanced config |
| config-template.toml | Configuration reference with 5 complete scenario examples |
| prompts/base_system_*.txt | System prompts for agent roles (analyst, creative, researcher, etc.) |

## Architecture at a Glance

```
[Initial Prompt]
    |
    v
Agent 1 (turn 1)
    |
    v
Router → [Agent 2, Agent 3]
    |
    v
Agent 2 (turn 2)
    |
    v
(continue until stop condition)
```

**Core components:**
1. **Session Manager** — Creates sessions, assigns IDs, manages logs
2. **Router** — Routes messages between agents based on topology
3. **Agent Manager** — Loads agent definitions from TOML config
4. **LLM Adapters** — Provider-specific drivers (normalize to one interface)
5. **Memory Manager** — Per-agent bounded context (window + rolling summary)
6. **Logging** — Human-readable logs + optional JSONL events
7. **Guardrails** — Loop detection, budget enforcement, convergence checks

## Next Steps

1. Read **[QUICKSTART.md](docs/QUICKSTART.md)** to run your first session
2. Explore **[GUIDE.md](docs/GUIDE.md)** for routing topologies and advanced scenarios
3. See `config-template.toml` for all available configuration options
4. Check `prompts/start_examples/` for example prompts to get started

## License

See LICENSE file.
