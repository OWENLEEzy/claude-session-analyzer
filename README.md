# claude-session-analyzer

Search Claude Code conversation history and resume past sessions.

## Requirements

- Python 3.10+
- Node.js 16+ (for npm install)

## Install

### Option 1: npm (recommended)

```bash
npm install -g claude-session-analyzer
```

This automatically installs the `/session-search` skill.

### Option 2: from source

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
```

Returns Session IDs to resume with:

```bash
claude --resume <session-id>
```

### CLI

```bash
# Search sessions
csa search "authentication"
csa search "fix bug" --limit 10

# Analyze a session file
csa analyze path/to/session.jsonl
```

## How it works

1. Scans `~/.claude/projects/*.jsonl`
2. Matches keywords against session content
3. Ranks results by relevance

## Development

```bash
uv sync            # install dependencies
just test          # run tests
just check         # lint + format + typecheck
```

## License

MIT
