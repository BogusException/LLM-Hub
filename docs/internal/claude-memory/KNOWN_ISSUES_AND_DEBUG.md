# Known Issues & Debugging Guide

## Current Known Issues

### 1. Live API Tests Fail with Invalid Keys
- **Status**: Expected behavior, not a bug
- **Details**: Google and Anthropic keys in config.toml are placeholders (sk-test...)
- **Impact**: Integration tests will report failures for these providers
- **Resolution**: Update API keys in config.toml with valid keys
- **Testing**: `pytest tests/test_integration_live.py -v`

### 2. ANTHROPIC_API_KEY Environment Variable Conflicts with OAuth
- **Status**: Resolved via env var naming change
- **Details**: Using `ANTHROPIC_API_KEY` interferes with OAuth process
- **Solution**: Renamed to `CLAUDE_KEY` (product-based naming convention)
- **Updated files**: config.py, config-template.toml, QUICKSTART.md, GUIDE.md, docs
- **Note**: All three providers now use product names (CHATGPT_KEY, CLAUDE_KEY, GEMINI_KEY)

## Debugging Techniques

### Enable Debug Logging
The system logs debug information to `logs/debug.log`. To view in real-time:
```bash
tail -f logs/debug.log
```

### Capture Full Session Output
Main session logs are at `logs/{session_id}.log`. View during session:
```bash
tail -f logs/*.log
```

### Check API Connectivity
Run the live integration test to validate credentials:
```bash
pytest tests/test_integration_live.py -v
```

This tests each provider individually and reports:
- Success/failure per provider
- Specific error messages from API
- Whether config.toml is properly formatted

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Using wrong path | Check current directory, use absolute path or `-c ./config.toml` |
| "Agent missing API key" | Key not in config or env var | Add to config or set env var with product name (CHATGPT_KEY, etc.) |
| "Invalid TOML syntax" | Malformed config | Run through TOML validator, check brackets and quotes |
| Session stops immediately | API error or bad config | Check `logs/debug.log` for error details |
| API rate limited | Too many requests | Reduce agents, reduce fanout, add cooldown_seconds, use limited fanout |
| High token usage | Memory window too large | Reduce keep_last_messages, enable summarization |
| Agents not responding | Adapter error | Verify provider name (openai, anthropic, google), check model name |
| Weird agent behavior | Bad system prompt | Verify system_prompt or system_prompt_file is valid |

## Performance Issues

### Session Running Out of Budget
If sessions consistently hit token limits:
1. Check `max_tokens_total` in config - increase if needed
2. Verify actual token usage in logs - might be different than expected
3. Try reducing memory window: `keep_last_messages = 6` instead of 12
4. Use limited fanout: `fanout = "limited_2"` instead of broadcast

### Slow Response Times
If agents are taking long time between turns:
1. Check network latency - try ping to provider API
2. Verify model availability (e.g., gpt-4 might have quota limits)
3. Check cooldown_seconds - might be intentionally delaying
4. Try simpler model: gpt-3.5-turbo instead of gpt-4

### Memory Issues (Out of Memory)
If Python process dies with OOM:
1. Reduce number of agents
2. Reduce memory window: `keep_last_messages = 6`
3. Reduce max_turns_total to end session sooner
4. Check for memory leaks in adapter code

## Testing & Validation

### Unit Tests
All 64 mock tests should always pass:
```bash
pytest -k "not live" -v
```

If any fail, it indicates a code logic error.

### Integration Tests
Conditional on valid config.toml:
```bash
pytest tests/test_integration_live.py -v
```

Expected results:
- Skip message if config.toml missing
- Pass/fail per provider depending on key validity
- Detailed error report if any fail

### Manual Session Validation
Run a short test session:
```bash
python -m src.hub --config config.toml --prompt-file prompts/start_examples/debate.txt
```

With short limits in config:
```toml
[session]
max_turns_total = 5
max_minutes = 2
max_tokens_total = 10000
```

Check:
- Session starts and logs appear
- Agents send messages to each other
- Logs are readable and in correct format
- Session ends cleanly after max_turns_total

## Git & Repository Issues

### Sensitive Files Accidentally Committed
The project has been through git history cleaning via filter-repo. This was necessary to remove:
- CLAUDE.md (development notes)
- docs/internal/ (internal docs)
- config.toml (API keys)

These are now properly gitignored. If you accidentally commit them in the future:
1. Use `git rm --cached {file}` to remove from index
2. Use `git filter-repo --invert-paths --path {file}` to remove from history
3. Force push: `git push origin --force-all`
4. Verify .gitignore includes the file pattern

### Line Ending Issues (CRLF vs LF)
If API key validation fails but keys look correct:
1. Check git config for line ending handling: `git config core.safecrlf`
2. Verify config.toml doesn't have CRLF: `file config.toml`
3. If needed, convert: `dos2unix config.toml` or in git: `git config core.autocrlf input`

## Documentation Notes

### Where Information Lives
- **Quick start**: QUICKSTART.md
- **Complete guide**: GUIDE.md
- **Feature overview**: README.md
- **Configuration reference**: config-template.toml (heavily commented)
- **Architecture**: CLAUDE.md and docs/internal/ (this folder)

### Keeping Docs in Sync
When changing code:
1. Update docstrings in code
2. Update relevant markdown docs
3. Update config-template.toml examples if applicable
4. Test that all references still work

### Documentation Issues Found & Fixed
- Missing ./docs/ folder reference in README (fixed: added docs/ to project structure)
- System prompt examples not documented (fixed: added to QUICKSTART.md with file:// examples)
- Cost warnings missing from README (fixed: added major warning section)
- ANTHROPIC_API_KEY env var naming conflict (fixed: changed to CLAUDE_KEY throughout)

## Future Work (If Needed)

Potential improvements not yet implemented:
- Performance optimization for large agent counts
- Conversation branching/multi-path support
- Persistent session state (pause and resume)
- Web UI for monitoring sessions
- Advanced metrics and analytics
- Custom topology definitions via config
- Plugin system for custom adapters
- Stream-based response handling for long outputs

All core functionality requested is complete and working.
