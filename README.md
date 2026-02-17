# claude-session-analyzer

Search Claude Code conversation history and resume past sessions.

## Features

- **Keyword Search** - Find sessions by topic
- **Time Filtering** - `--since yesterday`, `--since 7days`
- **Session Resume** - Returns Session IDs for `claude --resume`

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
