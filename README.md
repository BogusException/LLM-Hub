# LAN-LLM-Hub

A **configuration-driven multi-agent LLM orchestrator** that coordinates conversations between multiple language models across different providers (OpenAI, Anthropic, Google) and local models. Same engine, different configurations for debates, consensus-building, interrogations, adversarial testing, and design reviews.

## Features

- **Multi-provider support** — OpenAI (GPT-4, GPT-3.5), Anthropic (Claude), Google (Gemini), local models (Ollama)
- **Configurable topologies** — Hub-spoke, star, round-robin, mesh, arbiter-gated routing patterns
- **Per-agent memory management** — Bounded context with rolling summaries to control token costs
- **Budget enforcement** — Global and per-agent limits on turns, time, and tokens
- **Scenario presets** — 5 built-in scenarios (debate, consensus, interrogation, adversarial, design review)
- **Per-agent system prompts** — Inline or file-based (`file://` references) behavior customization
- **Private messages** — Support for evaluation-style scenarios with judge/arbiter agents
- **Guardrails** — Loop detection, convergence detection, and cost controls
- **Human-readable logs** — Tail-friendly session logs + optional JSONL event replay
- **Cost optimization** — Fanout strategies, memory tuning, and model selection guidance

## Quick Start

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# cp config-template.toml config.toml  # Copy template, then fill in API keys
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
tail -f logs/*.log
```

## Documentation

### [QUICKSTART.md](docs/QUICKSTART.md)
- Installation and initial setup
- Configuration essentials (session, agents, topology)
- Using system prompts and per-agent customization
- Step-by-step walkthrough of 5 scenario examples
- Environment variables alternative to inline API keys
- Troubleshooting common issues
- Running tests

### [GUIDE.md](docs/GUIDE.md)
- Routing Topologies — Hub-spoke, star, round-robin, mesh, arbiter
- Fanout Strategies — Broadcast modes and cost impact
- Memory Management — Window + rolling summary pattern, tuning
- Guardrails — Max turns, max tokens, loop/convergence detection
- Cost Optimization — 6 strategies ranked by impact, budget examples
- Public vs Private Messages — Evaluation scenarios
- Use Cases — Debate, consensus, interrogation, adversarial, design review
- Advanced Configuration — Temperature, max_tokens, memory, channels
- Statistics, Logging, Testing, Troubleshooting

## Project Structure

```
src/
├── hub.py                    # Main orchestration loop
├── session.py                # Session manager and agent definitions
├── router.py                 # Topology-based routing
├── memory.py                 # Per-agent bounded memory
├── guardrails.py             # Budget enforcement and stop conditions
├── adapters/                 # LLM provider drivers
└── utils/                    # Config parsing, logging, debug tools

docs/
├── QUICKSTART.md             # 5-minute setup and configuration guide
└── GUIDE.md                  # Complete feature reference and advanced topics

prompts/
├── start_examples/           # 5 scenario prompt files
└── base_system_*.txt         # Role-specific system prompts

config-template.toml          # 5 commented scenario examples (commit this)
config.toml                   # Local config with API keys (gitignore this)
```

## Core Concepts

**Seven components:**
1. **Session Manager** — Creates sessions, assigns IDs, manages logs
2. **Router** — Routes messages between agents based on topology
3. **Agent Manager** — Loads agent definitions from TOML
4. **LLM Adapters** — Provider-specific drivers
5. **Memory Manager** — Bounded context with rolling summaries
6. **Logging** — Tail-friendly logs + optional JSONL replay
7. **Guardrails** — Loop detection, budget enforcement, convergence

## Configuration Philosophy

- **Commit**: `config-template.toml` (examples only)
- **Never commit**: `config.toml` (has API keys)
- **Secrets**: Environment variables or local config
- **Scenarios**: Uncomment one of 5 examples, fill in keys, run

## Running

```bash
pytest                              # Run tests
pytest tests/test_integration_live.py  # Live API tests (needs config.toml)
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
```

## Cost & Token Usage Warning

**This program makes real API calls to LLM providers and will incur charges.** Each agent call consumes tokens at the rates set by your provider (OpenAI, Anthropic, Google, etc.). Token costs add up quickly.

**You are responsible for all charges incurred.** Before running any session:

1. **Understand token costs** — Read your provider's pricing
2. **Set aggressive limits** in `config.toml`:
   - `max_tokens_total` — Hard cap on session tokens
   - `max_turns_total` — Limit conversation length
   - `max_minutes` — Stop after N minutes elapsed
3. **Start small** — Test with 5-10 turns before longer runs
4. **Use cheaper models** — gpt-3.5-turbo, claude-3-haiku for experimentation
5. **Monitor logs** — Check `logs/*.log` during runs; stop if costs seem high

Example conservative config:
```toml
[session]
max_turns_total = 10           # Short session
max_tokens_total = 20000       # ~$0.50 on gpt-4
max_minutes = 5
```

**If you don't understand token costs or how to set limits, do not run this program until you do.** Runaway sessions can cost hundreds of dollars in minutes.

## Disclaimer

This software is provided as-is. **You are solely responsible for:**

- All costs incurred from API calls to LLM providers
- Understanding your provider's pricing and rate limits
- Setting appropriate budget limits in your configuration
- Monitoring usage and stopping sessions if needed
- Any errors, bugs, or unexpected behavior

The authors and maintainers of this project are not responsible for:
- Charges or billing issues with third-party LLM providers
- Loss of data or corrupted logs
- Unintended behavior or infinite loops (despite guardrails)
- Misuse or misconfiguration

**Use at your own risk.** Start with small, limited tests. Monitor costs carefully.

## License

See LICENSE file.
