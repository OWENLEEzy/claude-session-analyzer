---
name: session-search
description: Search Claude Code conversation history to find and resume past sessions. Use when user wants to find previous conversations about a topic.
---

# session-search

Search Claude Code conversation history to find and resume past sessions.

## When to Use

When user says:
- "Find sessions about [topic]"
- "Search for [keyword] conversations"
- "What was I working on [topic]"
- "上次的 [topic] 会话"
- "继续之前的 [topic] 工作"

## Usage

Run the skill's Python script:

```bash
python3 ~/.claude/skills/session-search/session-search.py "<query>"
```

## Output Format

```
Found 3 sessions matching "用户认证":

1. [abc123def456...] 2024-02-16 14:32  /Users/foo/projects/my-app
   Goals: 实现用户认证功能
   Actions: 创建 AuthModule, 添加 JWT 验证
   Outcome: success
   Resume: claude --resume abc123def456...
```

## Examples

| User Input | Command |
|------------|---------|
| "Find authentication sessions" | `python3 ~/.claude/skills/session-search/session-search.py "authentication"` |
| "Search for login bug" | `python3 ~/.claude/skills/session-search/session-search.py "login bug"` |

## Workflow

```
/session-search <query> -> Run Python Script -> Display Results
```
