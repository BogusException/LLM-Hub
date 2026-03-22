# Architecture Notes & Key Decisions

## Seven Core Components

1. **Session Manager** (session.py) - Creates sessions, assigns IDs, manages logs, tracks budgets
2. **Router** (router.py) - Routes messages between agents based on topology
3. **Agent Manager** (config.py) - Loads agent definitions from TOML config
4. **LLM Adapters** (adapters/) - Provider-specific drivers with normalized interface
5. **Memory Manager** (memory.py) - Per-agent bounded context with window + rolling summary
6. **Logging** (utils/logging.py) - Human-readable tail-friendly logs + optional JSONL replay
7. **Guardrails** (guardrails.py) - Loop/convergence detection, budget enforcement

## Key Design Patterns

### Configuration-First Approach
- All scenarios use same engine with different config presets (topology, agents, memory, stop conditions)
- TOML config is single source of truth
- No hardcoded behavior per use case

### Per-Agent Memory (Bounded Context)
- Window pattern: keep last N messages
- Rolling summary: when buffer exceeds threshold, summarize and discard old messages
- Prevents token explosion while maintaining conversation context

### Message Routing (Topology-Driven)
- Supported topologies: hub-spoke (default), star, round-robin, mesh, arbiter-gated
- Fanout control: broadcast_except_sender, limited_1, limited_2, broadcast_all
- Prevents n² message explosion in large agent groups

### Adapter Interface (Pluggable)
All adapters implement: `generate(messages, settings) -> (text, usage, latency)`
- Normalizes across OpenAI, Anthropic, Google, Ollama
- Error handling and rate limiting per provider
- Mock adapters for testing

### System Prompts (Flexible)
- Inline: `system_prompt = "text"`
- File-based: `system_prompt = "file://./prompts/base_system_analyst.txt"`
- Processed recursively by config loader
- Attitudes (1-2 sentence personas) compose into base prompt

### Cost Control Strategy
- Session limits: max_turns_total, max_minutes, max_tokens_total
- Per-agent limits: max_turns_per_agent
- Memory tuning: smaller window = fewer tokens
- Fanout control: limited recipients = fewer API calls
- Model selection: cheaper models for testing

## Important Code Patterns

### Config Loading (config.py)
```python
PRODUCT_NAMES = {
    "openai": "CHATGPT",
    "anthropic": "CLAUDE",
    "google": "GEMINI",
}
# API key resolution: config value -> env var (CHATGPT_KEY, etc.) -> error
```

### File Reference Processing (config.py)
- Recursive processing handles `file://` strings anywhere in config
- Both absolute and relative paths supported
- Loads system_prompt and system_prompt_file via same mechanism

### Error Diagnostics (hub.py)
- Detailed exception messages with provider name, model, specific error
- Points users to debug.log for additional context
- Distinguishes config errors, network errors, auth errors

### Logging Format (utils/logging.py)
- `YYYY-MM-DD hh:mm:ss: [AGENT_ID] <message>`
- Deterministic, tail-friendly
- Optional JSONL events for replay/debugging

## Testing Strategy

### Unit Tests (tests/)
- Router: topology logic with various agent configs
- Memory: window + summary behavior, edge cases
- Guardrails: budget exhaustion, loop/convergence detection
- Adapters: interface compliance with mocks

### Integration Tests (tests/test_integration_live.py)
- Skips gracefully if config.toml missing (CI/CD)
- Tests each provider individually
- Reports detailed diagnostics if any fail
- Validates actual API connectivity

## Configuration Schema Essentials

```toml
[session]
topology = "hub_spoke"           # or star, round_robin, mesh, arbiter_gated
fanout = "broadcast_except_sender"
keep_last_messages = 12          # Memory window
max_turns_total = 100            # Session stop condition
max_minutes = 60                 # Session stop condition
max_tokens_total = 100000        # Session stop condition

[[agents]]
id = "analyst"
provider = "openai"              # or anthropic, google, ollama
model = "gpt-4"
# api_key = "..." or use CHATGPT_KEY env var
temperature = 0.7
role = "analyst"
system_prompt = "file://./prompts/base_system_analyst.txt"
attitude = "Skeptical but fair."
private_notes = false            # For evaluation scenarios
subscriptions = ["main"]          # Channel subscriptions
```

## Environment Variable Naming

User preference for product-based naming (avoids conflicts):
- `CHATGPT_KEY` for OpenAI
- `CLAUDE_KEY` for Anthropic (not ANTHROPIC_API_KEY - conflicts with OAuth)
- `GEMINI_KEY` for Google

## Security Notes

- API keys must never be committed (use .env or config.toml, both gitignored)
- CLAUDE.md and docs/internal/ excluded from version control
- config-template.toml is committed (examples only, no keys)
- config.toml is gitignored (user's local keys)
