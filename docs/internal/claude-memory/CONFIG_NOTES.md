# Configuration Notes & Common Patterns

## File Organization

- **config-template.toml** - Committed to repo, contains 5 scenario examples (debate, consensus, interrogation, adversarial, design_review), no API keys, for reference
- **config.toml** - User's local config, gitignored, contains actual API keys and personal settings
- **prompts/base_system_*.txt** - Role-specific system prompts (analyst, creative, researcher, skeptic, mediator, architect, operations, product, defender, attacker, interrogator, actor, judge)
- **prompts/start_examples/*.txt** - Starting prompts for 5 scenarios

## Key Configuration Patterns

### Session Config
```toml
[session]
log_dir = "./logs"                    # Where to write session logs
topology = "hub_spoke"                # Routing topology
fanout = "broadcast_except_sender"    # Who receives messages
keep_last_messages = 12               # Memory window size
summarize_after_messages = 24         # When to trigger summary
max_turns_total = 100                 # Stop after N total turns
max_minutes = 60                      # Stop after N minutes
max_tokens_total = 100000             # Stop after N tokens consumed
max_turns_per_agent = null            # Optional: per-agent turn limit
cooldown_seconds = 0.0                # Delay between agent turns
```

### Agent Config
```toml
[[agents]]
id = "analyst"                                              # Unique ID
provider = "openai"                                         # openai, anthropic, google, ollama
model = "gpt-4"                                             # Model name
# api_key = "sk-..."                                        # Or use env var
temperature = 0.7                                           # 0.0-2.0
max_tokens = 2000                                           # Per-response limit
role = "analyst"                                            # Role in scenario
attitude = "Demands evidence, breaks down claims."          # 1-2 sentence persona
system_prompt = "file://./prompts/base_system_analyst.txt"  # Inline or file://
private_notes = false                                       # Can send private messages?
subscriptions = ["main"]                                    # Channel subscriptions
```

## API Key Resolution Order

For each agent, the code looks for API key in this order:
1. Inline in config: `api_key = "sk-..."`
2. Environment variable: Based on provider name
   - OpenAI → `CHATGPT_KEY`
   - Anthropic → `CLAUDE_KEY`
   - Google → `GEMINI_KEY`
3. If not found: Raises error with helpful message

Example error message:
```
Agent 'analyst' missing API key. Provide in config as api_key or set CHATGPT_KEY env var
```

## Scenario Presets

### 1. Debate
- 3 agents with different perspectives on a topic
- Topology: hub_spoke
- System prompts: base_system_analyst, base_system_skeptic, base_system_creative
- Start prompt: `prompts/start_examples/debate.txt`
- Use case: Multi-perspective discussion on any topic

### 2. Consensus
- 4 agents + 1 mediator working toward agreement
- Topology: hub_spoke
- System prompts: Include base_system_mediator
- Start prompt: `prompts/start_examples/consensus.txt`
- Use case: Collaborative problem-solving, team alignment

### 3. Interrogation (Turing Test)
- 1 actor + 2 interrogators + 1 judge
- Topology: star (judge at center)
- System prompts: base_system_actor, base_system_interrogator, base_system_judge
- Start prompt: `prompts/start_examples/interrogation.txt`
- Use case: Human/AI assessment, evaluation scenarios
- Key feature: Private notes (judge can send private assessments)

### 4. Adversarial Testing
- 1 defender + 2 attackers
- Topology: star or mesh
- System prompts: base_system_defender, base_system_attacker
- Start prompt: `prompts/start_examples/adversarial.txt`
- Use case: Security testing, vulnerability finding, design critique

### 5. Design Review
- 1 architect + 1 ops + 1 product + 1 mediator
- Topology: hub_spoke
- System prompts: base_system_architect, base_system_operations, base_system_product, base_system_mediator
- Start prompt: `prompts/start_examples/design_review.txt`
- Use case: Multi-stakeholder technical planning

## Fanout Strategies (Message Distribution)

- **broadcast_except_sender** - Everyone except who sent it (most common)
- **limited_1** - Only 1 other agent (round-robin)
- **limited_2** - Only 2 other agents (helps with scale)
- **broadcast_all** - Everyone including sender (rare, for global announcements)

Impact on cost: fewer recipients = fewer API calls = lower cost

## Memory Window Tuning

Smaller window = fewer tokens = lower cost but less context
Larger window = more context but higher cost

Example conservative config:
```toml
keep_last_messages = 6            # Only last 3 exchanges per agent
summarize_after_messages = 12     # Summarize often
```

## Cost Optimization Strategies (Ranked by Impact)

1. **Reduce max_turns_total** - Most direct cost reduction (fewer turns = fewer API calls)
2. **Reduce number of agents** - Fewer agents = fewer parallel API calls
3. **Use limited fanout** - limited_1 or limited_2 instead of broadcast
4. **Reduce memory window** - Smaller window = fewer tokens per message
5. **Use cheaper models** - gpt-3.5-turbo instead of gpt-4, claude-3-haiku instead of claude-3-opus
6. **Switch topology** - star or mesh can be more efficient than full broadcast

## Important TOML Syntax Notes

- No null values: Use comment-out or empty string instead
  - ✅ Correct: `# max_turns_per_agent = ""`
  - ❌ Wrong: `max_turns_per_agent = null`
- File paths in `file://` references can be relative or absolute
- Temperature valid range: 0.0 (deterministic) to 2.0 (very creative)
- All numeric values must be valid TOML (not quoted)

## Environment Variables

Set before running hub:
```bash
export CHATGPT_KEY="sk-..."
export CLAUDE_KEY="sk-ant-..."
export GEMINI_KEY="AIzaSy..."
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
```

Or leave inline in config and set environment variables as backup.

## Error Handling

Hub.py catches API errors and provides detailed diagnostics:
- Provider name, model, operation
- Specific error from API
- Suggestion: check debug.log
- Points user toward config validation

Check `logs/debug.log` for detailed error messages and stack traces.
