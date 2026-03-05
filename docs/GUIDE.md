# Comprehensive Guide

This guide covers routing topologies, memory management, guardrails, use cases, and advanced configuration.

## Routing Topologies

Different topologies route messages between agents in different patterns. Choose based on your scenario.

### Hub-Spoke (Default)

The orchestrator is the central hub. All agents communicate through it.

**How it works:**
- Initial prompt → all agents
- Each agent response → hub
- Hub forwards response to all other agents (optionally excluding sender)
- Controlled, simple, and scalable

**Best for:** Debates, consensus, general multi-agent discussions

**Configuration:**
```toml
[session]
topology = "hub_spoke"
fanout = "broadcast_except_sender"  # Don't echo messages back to sender
```

**Fanout modes:**
- `broadcast_except_sender`: Default. All agents except sender receive message
- `broadcast_all`: Unusual, but all agents receive (including sender)
- `limited_1`: Only one recipient per message (cost control)
- `limited_2`: Only two recipients per message (partial fanout)

### Star (Actor + Interrogators)

One central "actor" agent converses with multiple "interrogator" agents that don't talk to each other.

**How it works:**
- Actor broadcasts to all interrogators
- Each interrogator sends to actor only
- Interrogators do NOT talk to each other (reduces chaos)
- Optional judge collects private confidences and decides when done

**Best for:** Turing-style tests, human detection harnesses, interrogation scenarios

**Configuration:**
```toml
[session]
topology = "star"

[[agents]]
id = "actor"
role = "actor"
# This agent will broadcast to all interrogators

[[agents]]
id = "interrogator1"
role = "interrogator"
# This agent sends to actor only

[[agents]]
id = "judge"
role = "judge"
# Can be arbiter or summarizer
```

### Round Robin

Agents speak in rotation, one per turn.

**How it works:**
- Turn 1: Agent 1 speaks
- Turn 2: Agent 2 speaks
- Turn 3: Agent 3 speaks
- Turn 4: Agent 1 speaks again (rotation continues)

**Best for:** Structured discussions, controlled debates, cost management

**Configuration:**
```toml
[session]
topology = "round_robin"
```

### Mesh

Everyone talks to everyone.

**How it works:**
- Every agent receives every message from every other agent
- High connectivity, high token burn

**Best for:** Small groups (2-3 agents), high interactivity needed

**Configuration:**
```toml
[session]
topology = "mesh"
```

**Warning:** Token costs scale with O(n²). Recommend with `limited_2` fanout and aggressive time/turn limits.

### Arbiter / Moderator-Gated

One "arbiter" agent controls the flow.

**How it works:**
- Arbiter decides who speaks next
- Arbiter decides what gets forwarded to whom
- Useful for moderated discussions or filtered communication

**Best for:** Expert panels, moderated debates, filtered intelligence gathering

**Configuration:**
```toml
[session]
topology = "arbiter_gated"

[[agents]]
id = "arbiter"
role = "arbiter"
# This agent decides routing

[[agents]]
id = "expert1"
role = "expert"
# Speaks when arbiter allows

[[agents]]
id = "expert2"
role = "expert"
```

## Fanout Strategy (Message Broadcasting)

When an agent speaks, fanout controls who receives the message. Only applies to `hub_spoke` topology.

### Strategy Options

**`broadcast_except_sender`** (default, recommended)
- All agents except the speaker receive the message
- Prevents echo/confusion
- Good for balanced discussions
- Cost: O(n) messages per turn where n = agent count

**`broadcast_all`**
- All agents including speaker receive their own message
- Unusual; can create confusion or echo effects
- Cost: O(n) messages per turn

**`limited_1`**
- Only 1 random agent receives message each turn
- Extreme cost control
- Minimal interaction; agents may miss context
- Cost: O(1) messages per turn

**`limited_2`**
- 2 random agents receive message each turn
- Balanced cost/interaction trade-off
- Good when token budget is tight
- Cost: O(2) messages per turn

### Configuration

```toml
[session]
topology = "hub_spoke"
fanout = "broadcast_except_sender"  # Default
```

### Cost Considerations

For 5 agents per turn:
- `broadcast_except_sender`: 4 messages × 5 calls = high cost per turn
- `limited_2`: 2 messages × 5 calls = ~50% cost reduction
- `limited_1`: 1 message × 5 calls = ~80% cost reduction

**Recommendation:** Start with `broadcast_except_sender` for small teams (2-3 agents). For 4+ agents and tight budgets, use `limited_2` or `round_robin` topology.

## Memory Management

Memory is per-agent and bounded. The hub maintains a sliding window of recent messages plus optional rolling summaries for older content.

### Window + Rolling Summary Pattern

Each agent's memory consists of:

1. **Rolling Summary** — Compact representation of older messages
2. **Recent Messages Window** — Last N messages verbatim

When history exceeds a threshold, the oldest messages are summarized and discarded.

**Example:**
- Conversation has 40 messages total
- Window size = 12 messages
- Summarization threshold = 24 messages
- Result: last 12 messages + 1 summary + newest incoming message

This keeps token costs bounded while maintaining context continuity.

### Configuration

```toml
[session]
keep_last_messages = 12          # Size of recent window
summarize_after_messages = 24    # Trigger summary at this count
```

**Tuning:**
- Larger window = more context, higher token cost
- Smaller window = less context, cheaper but might lose conversation flow
- Summarization threshold = when to compact old messages

### How It Works in Practice

Each agent call includes:

1. System prompt (+ attitude)
2. Session constraints
3. Rolling summary (if exists)
4. Last 12 messages (verbatim)
5. New incoming message

This structure keeps:
- **Cost bounded** — Fixed token count per agent call
- **Context preserved** — Recent messages are verbatim, older context is summarized
- **Conversation continuity** — Agents can reference earlier discussion in summary

## Guardrails

Guardrails prevent runaway conversations and enforce budgets.

### Global Limits

Stop the entire session after:

```toml
[session]
max_turns_total = 80        # Stop after 80 total turns
max_minutes = 30            # Stop after 30 minutes
max_tokens_total = 100000   # Stop after 100k tokens consumed
```

### Per-Agent Limits

```toml
[[agents]]
id = "agent1"
max_turns_per_agent = 20    # This agent speaks max 20 times
cooldown_seconds = 5        # This agent waits 5s between turns
```

### Loop Detection

If an agent repeats the same message 3+ times consecutively, the orchestrator flags it as looping and can mute the agent or stop the session.

**Algorithm:**
- Hash each agent's message
- Count consecutive identical hashes
- If count ≥ 3: loop detected

**Limitations:** Detects exact duplicates, not semantic repetition. Complemented by convergence detection.

### Convergence Detection

If the last 5 messages show minimal novelty (fewer than 2 unique hashes), the conversation has converged.

**Use case:** Detect when agents have agreed and further discussion won't add value.

**Limitations:** Simple heuristic. May flag genuine agreement as "convergence."

## Public vs Private Messages

Support both to enable evaluation and scoring scenarios.

### Public Messages
Shared in the conversation. All agents receive them.

### Private Messages / Notes
Logged but only sent to designated recipients (e.g., judge, arbiter).

**Example (Star topology interrogation):**

Interrogators produce:
1. **Public:** The next question to ask the actor
2. **Private:** Confidence score + reasoning ("human probability 0.72 because…")

Only the judge receives the private notes.

**Configuration:**

```toml
[[agents]]
id = "interrogator"
private_notes = true       # This agent can send private messages
```

## Cost Optimization

Token usage is your primary cost driver. Use these strategies to control spend:

### Token Budget Estimation

Rough formula per agent call:
```
tokens ≈ (system_prompt_length + memory_window_size + incoming_message) / 4 + output_tokens
```

Example: 10 agents, 20 turns, 2000 token output per agent
```
Estimated cost: 10 × 20 × (500 input tokens + 2000 output) ≈ 500k tokens
```

### Cost Reduction Levers (Ranked by Impact)

1. **Reduce `max_turns_total`** (highest impact)
   - 20 turns instead of 100 = 80% savings
   - Trade-off: Less time for discussion

2. **Reduce agent count**
   - 3 agents instead of 5 = 40% savings per turn
   - Trade-off: Less diversity of perspective

3. **Use `limited_1` or `limited_2` fanout**
   - Limited_2 = ~50% cost vs broadcast
   - Limited_1 = ~80% cost vs broadcast
   - Trade-off: Some agents miss context

4. **Reduce `keep_last_messages` window**
   - 6 messages instead of 12 = ~50% memory cost
   - Trade-off: Risk losing conversation context

5. **Use cheaper models**
   - gpt-3.5 instead of gpt-4 = 75% savings
   - claude-3-haiku instead of sonnet = 67% savings
   - Trade-off: Lower quality responses

6. **Switch to `round_robin` topology**
   - One agent per turn vs multiple = lower message count
   - Trade-off: More linear, less interactive

### Example: Budget-Conscious Configuration

```toml
[session]
topology = "hub_spoke"
fanout = "limited_2"           # Only 2 recipients per message
max_turns_total = 20           # Short session
keep_last_messages = 6         # Smaller memory window
max_tokens_total = 50000       # Hard budget cap

[[agents]]
id = "gpt35_analyst"
provider = "openai"
model = "gpt-3.5-turbo"        # Cheaper than gpt-4
temperature = 0.5
max_tokens = 1000              # Shorter responses
```

### Example: Quality-Focused Configuration

```toml
[session]
topology = "hub_spoke"
fanout = "broadcast_except_sender"  # Full context sharing
max_turns_total = 50
keep_last_messages = 20        # Large context window
max_tokens_total = 200000      # Generous budget

[[agents]]
id = "gpt4_analyst"
provider = "openai"
model = "gpt-4"                # Best quality
temperature = 0.7
max_tokens = 2000              # Detailed responses
```

## Use Cases

All implemented with the same engine, different config.

### 1. Debate

Two or more agents with opposing views discuss a topic.

**Configuration:**
```toml
[session]
topology = "hub_spoke"
max_turns_total = 40

[[agents]]
id = "proponent"
attitude = "Argue strongly for AI safety as humanity's top priority."

[[agents]]
id = "skeptic"
attitude = "Question the urgency. Point out costs and tradeoffs."

[[agents]]
id = "mediator"
attitude = "Look for common ground. Summarize areas of agreement."
```

### 2. Consensus / Design Review

Different roles work toward agreement.

**Configuration:**
```toml
[session]
topology = "hub_spoke"
max_turns_total = 30

[[agents]]
id = "builder"
attitude = "Implementation-focused. What's the concrete next step?"

[[agents]]
id = "analyst"
attitude = "Data-driven. What are the metrics? What's the evidence?"

[[agents]]
id = "skeptic"
attitude = "Find risks and edge cases. Where could this fail?"

[[agents]]
id = "summarizer"
attitude = "Synthesize the discussion. What did we agree on?"
```

### 3. Interrogation Harness (Turing Test Style)

One agent attempts to convince others it's human.

**Configuration:**
```toml
[session]
topology = "star"
max_turns_total = 50
max_minutes = 20

[[agents]]
id = "actor"
role = "actor"
attitude = "Respond naturally and conversationally. Maintain continuity."

[[agents]]
id = "interrogator_skeptic"
role = "interrogator"
private_notes = true
attitude = "Skeptical interviewer. Probe for LLM tells and inconsistencies."

[[agents]]
id = "interrogator_linguist"
role = "interrogator"
private_notes = true
attitude = "Linguist. Focus on natural speech patterns and repair."

[[agents]]
id = "judge"
role = "judge"
attitude = "Collect confidences. Decide if sufficient evidence exists."
```

### 4. Adversarial Testing

One agent finds flaws; another defends.

**Configuration:**
```toml
[session]
topology = "hub_spoke"
max_turns_total = 25

[[agents]]
id = "attacker"
attitude = "Try to find edge cases and logical flaws."

[[agents]]
id = "defender"
attitude = "Defend your reasoning. Respond to critiques."

[[agents]]
id = "arbiter"
attitude = "Assess the quality of arguments from both sides."
```

## Advanced Configuration

### Using File References for Large Values

For long attitudes or system prompts, use `file://` to keep config clean:

```toml
[[agents]]
id = "agent1"
attitude = "file://./prompts/agent1_attitude.txt"
system_prompt = "file://./prompts/agent1_system.txt"
```

**System Prompts vs Attitudes:**
- `system_prompt`: Detailed instructions for how the agent should behave (sent as system message to LLM)
- `attitude`: Short persona directive (1-2 sentences, appended to system prompt)

When both are provided, they're combined: system_prompt + attitude. This lets you have a base system prompt for all agents while giving each a unique persona.

**Note on `private_notes`:** Set to `true` for agents that should send private messages (useful in star topology with judges/arbiters). Currently routes the same as public messages.

**Note on `subscriptions`:** Reserved for future channel-based routing. Currently all agents are on the "main" channel.

### Multiple Instances of the Same Model

Define different agent IDs with different personas:

```toml
[[agents]]
id = "gpt4_analytical"
provider = "openai"
model = "gpt-4"
temperature = 0.5
attitude = "Analytical and data-focused. Look for patterns."

[[agents]]
id = "gpt4_creative"
provider = "openai"
model = "gpt-4"
temperature = 0.9
attitude = "Creative and imaginative. Explore unconventional ideas."
```

### Mixed Providers

```toml
[[agents]]
id = "openai_agent"
provider = "openai"
model = "gpt-4"

[[agents]]
id = "claude_agent"
provider = "anthropic"
model = "claude-3-sonnet"

[[agents]]
id = "gemini_agent"
provider = "google"
model = "gemini-1.5-pro"
```

## Statistics and Analysis

Every session generates a stats file for learning about LLM behavior across runs.

### Stats File Format

Located in `./logs/{session_id}.stats.json`, contains:

**Summary metrics:**
- Duration (seconds)
- Number of turns completed
- Why session ended (convergence, max_turns, max_tokens, loop detected, error)
- Total tokens consumed
- Average tokens per turn

**Per-agent metrics:**
- Messages sent/received
- Tokens in/out
- Response latencies (min, max, average)
- Error count

**Routing metrics:**
- Total messages routed
- Average recipients per message

**Memory metrics:**
- Summarization events triggered
- Messages summarized

**Example summary:**
```json
{
  "session_id": "20260304153022",
  "duration_seconds": 47.3,
  "turns_completed": 23,
  "end_reason": "convergence_detected",
  "summary": {
    "total_tokens": 34821,
    "avg_tokens_per_turn": 1514.8
  },
  "agents": {
    "gpt4_analyst": {
      "messages_sent": 8,
      "tokens_in": 5200,
      "tokens_out": 4100,
      "avg_latency_ms": 1230.0
    }
  }
}
```

### Analyzing Across Runs

Since each run has its own stats file, you can:
- Compare different topologies with same agents
- Track cost trends across runs
- Identify which agents are most/least active
- Benchmark provider performance (OpenAI vs Anthropic vs Google)
- See which configurations lead to convergence vs loops

Example analysis script:
```bash
# View latest run
cat logs/*.stats.json | tail -1 | jq .

# Compare all agents across all runs
jq '.agents | keys[]' logs/*.stats.json | sort | uniq -c

# Find most expensive runs
jq '.summary.total_tokens' logs/*.stats.json | sort -rn | head -5
```

## Logging

Session logs are human-readable and tail-friendly.

### Session Log Format

Located in `./logs/{session_id}.log`:

```
2026-03-04 15:30:22: [HUB] Session created with 3 agents
2026-03-04 15:30:23: [agent1] Here's my first response...
2026-03-04 15:30:24: [agent2] I disagree because...
2026-03-04 15:30:25: [HUB] Loop detected: agent1 repeating
2026-03-04 15:30:25: [HUB] SESSION END: Loop detected
```

**Useful commands:**
```bash
tail -f logs/20260304153022.log          # Watch in real-time
grep "agent1" logs/20260304153022.log    # Filter by agent
grep "ERROR" logs/20260304153022.log     # Find errors
```

### Machine-Readable Events (Optional)

JSONL format in `./logs/{session_id}.events.jsonl`:

```json
{"timestamp": "2026-03-04 15:30:23", "sender": "agent1", "event_type": "message", "content": "...", "turn": 1, "input_tokens": 50, "output_tokens": 20, "latency_ms": 2340.5}
```

Useful for programmatic analysis, replay, and cost tracking.

## Testing

Run tests to verify everything works:

```bash
pytest                          # All tests
pytest tests/test_router.py     # Router topologies
pytest tests/test_memory.py     # Memory management
pytest tests/test_guardrails.py # Guardrails
pytest -v                       # Verbose output
```

Test coverage includes:
- LLM adapters (mocked HTTP requests)
- Routing topologies (all 5 types with various agent counts)
- Memory (window + summary behavior)
- Guardrails (budgets, loop detection, convergence)
- Configuration loading and validation

## Troubleshooting

### Session Stops Unexpectedly

Check `./logs/debug.log` for detailed error info. Common causes:
- API key invalid or expired
- Network connectivity issue
- Agent timeout

**Solution:** Fix the root cause and retry.

### Low Novelty / Agents Repeating

Agents are saying the same things.

**Solutions:**
- Increase agent temperature (0.7 → 0.9) for more variety
- Change agent attitudes to give different perspectives
- Reduce `keep_last_messages` so agents don't see full history (forces fresh thinking)
- Add a new agent with a different role

### Too Many Tokens / Budget Exceeded

Session is too expensive.

**Solutions:**
- Set `max_tokens_total` to enforce a hard budget
- Reduce `keep_last_messages` (smaller window = fewer tokens per call)
- Reduce `max_turns_total` (fewer turns = lower cost)
- Use cheaper models (gpt-3.5 instead of gpt-4)
- Use `topology = "round_robin"` or `limited_2` fanout

### Token Cost Estimation

The hub estimates tokens as: **4 characters ≈ 1 token**

This is a rough approximation. Actual tokenization varies by model. For precise budgeting, integrate an actual tokenizer or track real usage from API responses.

## See Also

- **[QUICKSTART.md](QUICKSTART.md)** — Getting started
- **config-template.toml** — Configuration reference with 5 complete scenario examples
- **prompts/base_system_*.txt** — System prompts for agent roles (analyst, creative, researcher, skeptic, mediator, architect, operations, product, attacker, defender, judge, interrogator, actor)
- **prompts/start_examples/** — Prompt templates for each scenario type
