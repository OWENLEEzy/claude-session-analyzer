# Claude Session Analyzer

Search Claude Code conversation history and resume past sessions.

## Quick Start

```bash
# Install (npm - recommended)
npm install -g claude-session-analyzer

# Or install (pip)
uv sync

# Search sessions
uv run csa search "authentication"

# Analyze a session
uv run csa analyze path/to/session.jsonl
```

## Common Commands

```bash
# Code quality
just check          # lint + format + mypy
just fmt            # format code
just typecheck      # type check

# Tests
just test           # run tests
just coverage       # tests + coverage

# Full check (before commit)
just full           # quick + security + test
```

## Project Structure

```
analyzer/
├── __init__.py       # Package exports
├── cli.py            # CLI (csa command)
├── core.py           # NLP analysis core
├── smart_search.py   # Session search
├── intent_analyzer.py # Intent analysis (LLM)
└── reranker.py       # Result reranking

skills/
└── session-search.md # Claude Code Skill definition

bin/
└── csa.js            # npm CLI entry

scripts/
└── postinstall.js    # npm postinstall (installs Skill)
```

## Key Features

1. **Session Search** - Search `~/.claude/projects/` for past sessions
2. **Resume Sessions** - Returns Session IDs for `claude --resume`
3. **NLP Analysis** - Extracts goals, actions, outcomes
4. **Claude Code Skill** - `/session-search` command

## Architecture

```
npm install -g claude-session-analyzer
         ↓
    Installs Skill + Python code
         ↓
/session-search <query> in Claude Code
         ↓
Python searches ~/.claude/projects/
         ↓
Returns results with Session IDs
         ↓
User copies claude --resume <ID>
```

## Code Standards

- Python 3.10+
- Ruff for lint/format
- Mypy for type checking (strict)
- Test coverage: 80%+

## Notes

- `mode` parameter in smart_search.py is intentionally unused (kept for API compatibility)
- jieba and rich need `ignore_missing_imports = true` (configured in pyproject.toml)
