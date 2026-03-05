# Quick Start Guide

Get LAN-LLM-Hub running in 5 minutes.

## 1. Install Dependencies

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Create Config File

Copy the template and fill in your API keys:

```bash
cp config-template.toml config.toml
```

Edit `config.toml`:
- Add `api_key` values for each agent, OR set environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`)
- Define at least one `[[agents]]` section with provider, model, and role

Example minimal config:
```toml
[session]
topology = "hub_spoke"
max_turns_total = 20
max_minutes = 10

[[agents]]
id = "agent1"
provider = "openai"
model = "gpt-4"
api_key = "sk-..."

[[agents]]
id = "agent2"
provider = "anthropic"
model = "claude-3-haiku"
api_key = "sk-ant-..."
```

## 3. Create a Prompt File (or use one)

Option A: Use an example
```bash
cat prompts/start_examples/debate.txt
```

Option B: Create your own
```bash
echo "Have a debate about AI safety. Agent1 argues it's the top priority. Agent2 is skeptical." > prompts/custom.txt
```

## 4. Run a Session

```bash
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
```

**What is `src.hub`?**

`python -m src.hub` runs the module `hub.py` inside the `src/` package as a script. Think of it like:
- `src/` = a namespace/module folder (contains `__init__.py`)
- `hub.py` = the main file to execute
- `python -m` = "run this module as the main program"

It's equivalent to running a main file directly. The `-m` flag tells Python to treat it as an executable module.

Or pass the prompt directly:
```bash
python -m src.hub --config config.toml -p "Debate the merits of Python vs Rust"
```

## 5. View Results

Session logs are in `./logs/`:

```bash
# Watch the session in real-time
tail -f logs/*.log

# View the full log when done
cat logs/20260304153022.log
```

## Configuration Essentials

### Agents Section

Each agent needs:
- `id`: Unique identifier
- `provider`: openai, anthropic, or google
- `model`: Model name (gpt-4, claude-3-haiku, gemini-1.5-pro, etc.)
- `api_key`: API key (or leave empty to use environment variable)

Optional:
- `temperature`: 0.0–2.0 (default 0.7)
- `max_tokens`: Max response length (default 2000)
- `attitude`: 1–2 sentence persona ("Skeptical analyst", etc.)
- `role`: Role in scenario (actor, interrogator, analyst, etc.)
- `system_prompt`: System prompt text or file reference (use `file://./path/to/file.txt` to load from file)
- `private_notes`: true/false (default false) — whether agent can send private messages
- `subscriptions`: List of channels agent subscribes to (advanced)

### Session Settings

- `topology`: hub_spoke (default), star, round_robin, mesh, arbiter_gated
- `max_turns_total`: Stop after N turns
- `max_minutes`: Stop after N minutes
- `max_tokens_total`: Stop after N tokens consumed
- `keep_last_messages`: Memory window size (default 12)

See `config-template.toml` for all options.

## Using System Prompts and Scenarios

The `prompts/` directory contains ready-to-use configurations:

### Start Examples (Scenario Prompts)
Each file in `prompts/start_examples/` is a starting prompt for a scenario:
- **debate.txt** — Debate on AI impact
- **consensus.txt** — Rate-limiting system design
- **interrogation.txt** — Turing test / human assessment
- **adversarial.txt** — Two-factor auth security testing
- **design_review.txt** — Microservices migration planning

Run with: `python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt`

### Agent System Prompts
The `prompts/base_system_*.txt` files define role-specific behavior:

Common roles:
- `base_system_analyst.txt` — Demands evidence, breaks down claims
- `base_system_creative.txt` — Generates novel ideas, explores unconventional angles
- `base_system_researcher.txt` — Validates against sources and best practices
- `base_system_skeptic.txt` — Probes for flaws and edge cases
- `base_system_mediator.txt` — Finds common ground, synthesizes views

Scenario-specific roles:
- `base_system_architect.txt`, `base_system_operations.txt`, `base_system_product.txt` — Design review
- `base_system_defender.txt`, `base_system_attacker.txt` — Adversarial testing
- `base_system_interrogator.txt`, `base_system_actor.txt` — Interrogation harness
- `base_system_judge.txt` — Evaluation and scoring

**Using system prompts in config:**
```toml
[[agents]]
id = "analyst_agent"
provider = "openai"
model = "gpt-4"
system_prompt = "file://./prompts/base_system_analyst.txt"
attitude = "Skeptical but open-minded."  # Optional: add brief persona
```

### 5 Complete Scenario Examples

The `config-template.toml` includes 5 fully configured examples ready to uncomment:
1. **Debate** (3 agents, hub-spoke) — Topic-based discussion with different perspectives
2. **Consensus** (4 agents + mediator, hub-spoke) — Collaborative problem-solving toward agreement
3. **Interrogation** (actor + 2 interrogators + judge, star topology) — Turing test / human assessment
4. **Adversarial Testing** (defender + 2 attackers, star topology) — Design critique and vulnerability testing
5. **Design Review** (architect + ops + product + mediator, hub-spoke) — Multi-stakeholder planning

**How to use a scenario:**

1. Open `config.toml` in your editor
2. Find the scenario you want (e.g., `# SCENARIO 1: DEBATE`)
3. Uncomment the entire `[session]` block and all `[[agents]]` entries
4. Replace placeholder API keys:
   - `"sk-..."` → your OpenAI key
   - `"sk-ant-..."` → your Anthropic key
   - `"AIzaSy..."` → your Google key
5. Optionally adjust `max_turns_total`, `max_minutes`, `temperature`, etc.
6. Run: `python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt`
7. Watch session logs: `tail -f logs/*.log`

Each scenario has built-in system prompts (via `file://./prompts/base_system_*.txt`) and role definitions, so you just need API keys.

## Using Environment Variables Instead

Instead of storing API keys in `config.toml`, use environment variables:

```bash
export CHATGPT_KEY="sk-..."
export CLAUDE_KEY="sk-ant-..."
export GEMINI_KEY="AIzaSy..."

python -m src.hub --config config.toml --prompt-file prompts/start.txt
```

In `config.toml`, leave `api_key` blank or omit it:
```toml
[[agents]]
id = "agent1"
provider = "openai"
model = "gpt-4"
# api_key line omitted—will use CHATGPT_KEY
```

## Troubleshooting

### "Config file not found"
```bash
cp config-template.toml config.toml  # Must create it first
```

### "Agent 'agent1' missing API key"
Either:
1. Add `api_key = "sk-..."` to the agent in `config.toml`, OR
2. Set environment variable: `export OPENAI_API_KEY="sk-..."`

### "Invalid TOML syntax"
Check your `config.toml` for typos. Use an online TOML validator if unsure.

### Session stops immediately
Check `./logs/debug.log` for detailed error messages. Common causes:
- API key is invalid or expired
- Network connectivity issue
- Agent produced an error

### No agents in config
Your `config.toml` must have at least one `[[agents]]` section.

## Next Steps

- Read **[GUIDE.md](GUIDE.md)** to understand routing topologies and memory management
- Check `config-template.toml` for complete reference with 5 scenario examples
- Explore `prompts/start_examples/` for prompt templates (debate, consensus, interrogation, adversarial, design_review)
- See `prompts/base_system_*.txt` for agent role system prompts

## Testing

Run the test suite to verify everything is installed correctly:

```bash
pytest                    # All tests
pytest tests/test_router.py  # Specific test file
pytest -v                 # Verbose output
```
