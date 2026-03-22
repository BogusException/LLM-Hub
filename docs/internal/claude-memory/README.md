# Claude Memory Files for LAN-LLM-Hub

This directory contains project state and context notes for Claude Code to use when the project is loaded in a new session.

## Files in This Directory

### STATUS.md
**Quick reference for project completion and current state**
- What's been completed
- Known issues and their status
- Next steps
- GitHub repository link
- Test results

Read this first to understand where the project stands.

### ARCHITECTURE_NOTES.md
**Design decisions, core components, and architectural patterns**
- Seven core components explanation
- Key design patterns (config-first, bounded memory, routing, adapters)
- Code patterns and implementations
- Testing strategy
- Security notes

Useful for understanding how things fit together and why design choices were made.

### CONFIG_NOTES.md
**Configuration patterns, scenarios, and tuning guidance**
- File organization (config-template.toml vs config.toml vs prompts)
- Session and agent configuration examples
- 5 scenario presets (debate, consensus, interrogation, adversarial, design_review)
- Fanout strategies and memory tuning
- Cost optimization strategies
- TOML syntax notes
- Environment variable details

Read when you need to understand configuration options or help user set up a new scenario.

### TESTING_STATUS.md
**Test coverage, validation, and how to run tests**
- Test summary (65 tests, 64 mock + 1 live)
- How to run different test subsets
- Validation checklist for when user updates API keys
- Code coverage information
- Known test status

Use when questions about testing come up, or to understand what's validated.

### KNOWN_ISSUES_AND_DEBUG.md
**Troubleshooting, debugging techniques, and issues encountered**
- Current known issues (with resolutions)
- Debugging techniques (enable logging, capture output, check connectivity)
- Common issues table (with causes and solutions)
- Performance issue troubleshooting
- Testing & validation procedures
- Git & repository issues
- Future work / potential improvements

Read when user encounters problems or asks about debugging.

---

## How to Use These Files

### When Starting a New Session with This Project

1. Quickly skim **STATUS.md** to see what's done
2. Check **KNOWN_ISSUES_AND_DEBUG.md** if anything seems broken
3. Keep **CONFIG_NOTES.md** handy when discussing scenarios or config changes
4. Reference **ARCHITECTURE_NOTES.md** if understanding design is needed

### User Questions

| User Question | Start Here |
|---------------|-----------|
| "What's left to do?" | STATUS.md |
| "How do I set up a debate?" | CONFIG_NOTES.md (Scenario Presets section) |
| "Why are agents doing X?" | ARCHITECTURE_NOTES.md |
| "Tests are failing" | TESTING_STATUS.md |
| "My session keeps stopping" | KNOWN_ISSUES_AND_DEBUG.md (Common Issues table) |
| "How do I reduce costs?" | CONFIG_NOTES.md (Cost Optimization) |
| "What's the project structure?" | ARCHITECTURE_NOTES.md (Seven Components) |

### Code Changes

When making code changes, consider updating:
- **ARCHITECTURE_NOTES.md** if you change a design pattern or component
- **CONFIG_NOTES.md** if you change configuration options or scenarios
- **KNOWN_ISSUES_AND_DEBUG.md** if you fix an issue
- **STATUS.md** with major completion milestones

---

## Key Information at a Glance

**Project Status**: Complete and deployed to GitHub
**Repository**: https://github.com/BogusException/LLM-Hub
**Test Results**: 64/64 mock tests passing, live tests pending valid API keys
**Last Updated**: 2026-03-05

**Critical Path**:
1. User updates API keys in config.toml
2. Run: `pytest tests/test_integration_live.py -v`
3. All providers should pass
4. Project is production-ready

**Five Scenario Presets Ready to Use**:
1. Debate (3 agents, discussion)
2. Consensus (4 agents + mediator, problem-solving)
3. Interrogation (1 actor + 2 interrogators + judge, evaluation)
4. Adversarial Testing (1 defender + 2 attackers, security)
5. Design Review (architect + ops + product + mediator, planning)

**User's Known Preferences** (see ~/.claude/CLAUDE.md):
- Single commit + push when all changes complete (never mid-task)
- Step-by-step instructions for multi-step tasks
- Skip explanations unless asked
- Ask about better approaches before implementing
- No em-dashes
- Ask clarifying questions rather than assume

---

## Notes for Next Session

When this project loads in a new shell:
1. These memory files exist at: `./docs/internal/claude-memory/`
2. They're separate from user-facing documentation (QUICKSTART.md, GUIDE.md, README.md in ./docs/)
3. They're gitignored (not in the repo, local only)
4. Update them as needed when project state changes

If the project structure changes significantly, organize this memory folder as needed. Current structure is:
```
docs/
├── QUICKSTART.md          (user-facing docs)
├── GUIDE.md               (user-facing docs)
├── README.md              (user-facing docs)
└── internal/
    └── claude-memory/
        ├── README.md      (this file)
        ├── STATUS.md
        ├── ARCHITECTURE_NOTES.md
        ├── CONFIG_NOTES.md
        ├── TESTING_STATUS.md
        └── KNOWN_ISSUES_AND_DEBUG.md
```
