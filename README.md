<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/NLP-powered-purple?style=for-the-badge" alt="NLP">
</p>

<h1 align="center">
  <pre>
   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
  ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
  ██║     ██║     ███████║██║   ██║██║  ██║█████╗
  ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
  ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
   ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
                  Session Analyzer
  </pre>
</h1>

<p align="center">
  <i>Search your Claude Code conversation history and resume past sessions</i>
</p>

---

## Features

- **Session Search** - Search all your Claude Code conversations using natural language
- **Resume Sessions** - Get Session IDs to continue past conversations with `claude --resume`
- **NLP Analysis** - Extract goals, actions, and outcomes from sessions automatically
- **Claude Code Skill** - Use `/session-search` directly in Claude Code

---

## Requirements

- **Python 3.10+** (for the core analyzer)
- **Node.js 16+** (for npm installation)
- **Anthropic API Key** (optional, for enhanced intent analysis)

---

## Installation

### Option 1: npm (Recommended)

```bash
npm install -g claude-session-analyzer
```

This installs:
- The `csa` CLI command
- The `/session-search` Skill for Claude Code

### Option 2: pip

```bash
pip install claude-session-analyzer
```

### Option 3: From Source

```bash
git clone https://github.com/your-repo/claude-session-analyzer.git
cd claude-session-analyzer
pip install -e ".[dev]"
```

---

## Usage

### As a Claude Code Skill

After npm installation, use directly in Claude Code:

```
/session-search authentication
```

**Output:**
```
Found 3 sessions matching "authentication":

1. [abc123def456...] 2024-02-16 14:32  /Users/foo/projects/my-app
   Goals: 实现用户认证功能
   Actions: 创建 AuthModule, 添加 JWT 验证
   Outcome: success
   Resume: claude --resume abc123def456...

2. [xyz789...] 2024-02-15 10:21  /Users/foo/projects/another
   Goals: 修复登录 bug
   Actions: 修改验证逻辑, 更新测试
   Outcome: success
   Resume: claude --resume xyz789...
```

Copy the `claude --resume <session-id>` command to continue that conversation.

### CLI Commands

```bash
# Search sessions
csa search "用户认证"
csa search "fix login bug"
csa search "上次的 React 项目" --limit 10

# Analyze a specific session file
csa analyze path/to/session.jsonl

# Output formats
csa search authentication --format json
csa search authentication --format table
csa analyze session.jsonl --format json
```

### Python API

```python
from analyzer import quick_search, SessionAnalyzer

# Search sessions
results = quick_search("authentication", limit=5)
for r in results:
    print(f"{r.session_id}: {r.summary}")
    print(f"  Resume: claude --resume {r.session_id}")

# Analyze a session file
analyzer = SessionAnalyzer()
result = analyzer.analyze("path/to/session.jsonl")
print(f"Goals: {result.goals}")
print(f"Actions: {result.actions}")
print(f"Outcome: {result.outcome}")
print(f"Confidence: {result.confidence}")
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     User Search Query                        │
│                   "authentication bug"                       │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Intent Analyzer (LLM)                      │
│              Extracts: auth, bug, login, JWT                 │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Local Session Searcher                          │
│          Scans ~/.claude/projects/*.jsonl                    │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Result Reranker                            │
│       Time decay + Project match + Similarity                │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Ranked Results with Session IDs                 │
│        Resume: claude --resume <session-id>                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Search Examples

| Query | Description |
|-------|-------------|
| `authentication` | Find sessions about auth features |
| `fix login bug` | Find bug-fixing sessions |
| `上次的 React 项目` | Search in Chinese |
| `recent API changes` | Find recent API work |
| `test coverage` | Find testing sessions |

---

## Output Format

### Search Output (JSON)

```json
{
  "session_id": "abc123def456...",
  "project_path": "/Users/foo/projects/my-app",
  "summary": "【目标】实现用户认证 → 【行动】创建模块 → 【结果】成功",
  "goals": ["实现用户认证功能"],
  "actions": ["创建 AuthModule", "添加 JWT 验证"],
  "outcome": "success",
  "similarity": 0.85,
  "timestamp": "2024-02-16T14:32:00"
}
```

### Analysis Output

```json
{
  "goals": ["实现用户认证功能"],
  "actions": ["创建 AuthModule", "添加 JWT 验证", "编写测试"],
  "outcome": "success",
  "confidence": 0.85,
  "summary": "【目标】实现用户认证 → 【行动】创建模块、添加验证 → 【结果】成功"
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | API key for enhanced intent analysis | No (fallback to keyword search) |

If no API key is set, the search uses a fallback keyword-based approach.

---

<details>
<summary><b>Development</b></summary>

### Setup

```bash
git clone https://github.com/your-repo/claude-session-analyzer.git
cd claude-session-analyzer
uv sync
```

### Run Tests

```bash
just test
# Or: uv run pytest tests/ -v
```

### Code Quality

```bash
just check     # lint + format + mypy
just fmt       # format code
just typecheck # type check
```

### Project Structure

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
```

</details>

---

<p align="center">
  <sub>Built for Claude Code power users who need to find and resume past conversations</sub>
</p>
