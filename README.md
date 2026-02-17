# claude-session-analyzer

Search Claude Code conversation history and resume past sessions.

## Features

- **Keyword Search** - Find sessions by topic
- **Time Filtering** - `--since yesterday`, `--since 7days`
- **Session Resume** - Returns Session IDs for `claude --resume`

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Installation Methods                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Claude Plugin  │      npm        │        Source               │
│  (recommended)  │                 │                             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ /plugin install │ npm install -g  │ git clone + uv sync         │
│ session-search  │ claude-session- │                             │
│                 │ analyzer        │                             │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Core Components                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   SKILL.md      │   CLI (csa)     │    Python Analyzer          │
│   Guide for     │   csa search    │    analyzer/                │
│   Claude        │   csa analyze   │    ├── cli.py               │
│                 │                 │    ├── core.py              │
│                 │                 │    ├── smart_search.py      │
│                 │                 │    ├── intent_analyzer.py   │
│                 │                 │    └── reranker.py          │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Source                             │
│                  ~/.claude/projects/*/*.jsonl                   │
│                    (Claude Code Session Files)                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Output                                 │
│   Session ID + Resume Command: claude --resume <session-id>    │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
claude-session-analyzer/
├── .claude-plugin/
│   ├── plugin.json         # Plugin metadata
│   └── marketplace.json    # Dev marketplace
├── skills/
│   └── session-search/
│       ├── SKILL.md        # Skill guide for Claude
│       └── session-search.py
├── analyzer/
│   ├── cli.py              # CLI entry point
│   ├── core.py             # NLP analysis
│   ├── smart_search.py     # Search logic + time filtering
│   ├── intent_analyzer.py  # Intent detection (LLM)
│   └── reranker.py         # Result ranking
├── bin/
│   └── csa.js              # npm CLI wrapper
├── package.json            # npm package config
└── pyproject.toml          # Python package config
```

## Requirements

- Python 3.10+
- Node.js 16+ (for npm install)

## Install

### Option 1: Claude Code Plugin (recommended)

```bash
# Add marketplace
claude /plugin marketplace add OWENLEEzy/claude-session-analyzer

# Install plugin
claude /plugin install session-search

# Restart Claude Code, then use:
/session-search 昨天做了什么
```

### Option 2: npm

```bash
npm install -g claude-session-analyzer
```

This automatically installs the `/session-search` skill.

### Option 3: from source

```bash
git clone https://github.com/OWENLEEzy/claude-session-analyzer.git
cd claude-session-analyzer
uv sync

# Install skill manually
mkdir -p ~/.claude/skills/session-search
cp skills/session-search/* ~/.claude/skills/session-search/
```

## Usage

### In Claude Code

```
/session-search authentication
/session-search 昨天做了什么
/session-search 最近一周的工作
```

Returns Session IDs to resume with:

```bash
claude --resume <session-id>
```

### CLI

```bash
# Keyword search
csa search "authentication" --limit 5

# Time filtering
csa search "" --since yesterday
csa search "" --since 7days --limit 10
csa search "" --since 2026-02-01 --until 2026-02-15

# List all sessions
csa search "" --all

# Analyze a session file
csa analyze path/to/session.jsonl

# JSON output
csa search "bug" --format json
```

## How it works

1. Scans `~/.claude/projects/*.jsonl`
2. Matches keywords against session content
3. Supports time filtering with relative dates
4. Ranks results by relevance

## Development

```bash
uv sync            # install dependencies
just test          # run tests
just check         # lint + format + typecheck
```

## License

MIT
