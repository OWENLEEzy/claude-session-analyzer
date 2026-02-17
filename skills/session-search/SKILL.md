---
name: session-search
description: 搜索 Claude Code 会话历史。根据用户意图使用不同的搜索方式。返回 Session ID 以便用 `claude --resume` 恢复会话。
---

# session-search

搜索 Claude Code 会话历史并返回 Session ID，用户可以用 `claude --resume <ID>` 恢复会话。

## 可用工具

### 1. csa search CLI（推荐）

主要的搜索工具，支持关键词搜索和时间过滤。

```bash
# 关键词搜索
csa search "<query>" --limit 5

# 时间范围过滤
csa search "" --since "2026-02-16" --until "2026-02-17" --limit 20
csa search "" --since "yesterday" --limit 10
csa search "" --since "7days" --limit 20

# 列出所有会话
csa search "" --all

# JSON 输出（便于程序处理）
csa search "<query>" --format json
```

**支持的相对日期**：
- `today` - 今天
- `yesterday` - 昨天
- `week` / `7days` - 最近 7 天
- `month` / `30days` - 最近 30 天
- `YYYY-MM-DD` - 具体日期

### 2. 直接列出会话文件

快速查看有哪些会话：

```bash
ls ~/.claude/projects/*/*.jsonl
```

### 3. 读取会话内容

需要详细信息时：

```bash
# 用 Python 读取会话时间和 ID
python3 -c "
import json
from pathlib import Path
from datetime import datetime

for f in Path('~/.claude/projects').expanduser().glob('*/*.jsonl'):
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    print(f'{mtime.strftime(\"%Y-%m-%d %H:%M\")}  {f.stem[:20]}...  {f.parent.name}')
"
```

## 使用指南

### 用户意图判断

根据用户的自然语言查询，选择合适的工具和参数：

| 用户说 | 意图 | 操作 |
|--------|------|------|
| "找 authentication 相关的会话" | 关键词搜索 | `csa search "authentication"` |
| "昨天做了什么" | 列出时间段 | `csa search "" --since yesterday` |
| "最近一周的工作" | 列出时间段 | `csa search "" --since 7days` |
| "上周的 React 项目" | 时间 + 项目 | 列出后筛选项目名 |
| "继续之前的认证工作" | 关键词搜索 | `csa search "认证"` |
| "找找关于数据库迁移的会话" | 关键词搜索 | `csa search "数据库迁移"` |

### 时间范围处理

Claude 理解自然语言中的时间概念：

1. **"昨天"** = `--since yesterday`
2. **"今天"** = `--since today`
3. **"最近一周"** / **"这周"** = `--since 7days`
4. **"上个月"** = `--since 30days`
5. **具体日期** = `--since 2026-02-01 --until 2026-02-15`

### 项目过滤

如果用户提到特定项目，可以在结果中筛选项目路径：

1. 先列出会话
2. 检查 `project_path` 字段
3. 筛选匹配的结果

### 输出格式

始终返回 Session ID 和 `claude --resume` 命令：

```
1. [abc123def456...] 2026-02-16 14:32  /Users/foo/projects/my-app
   Goals: 实现用户认证功能
   Actions: 创建 AuthModule, 添加 JWT 验证
   Outcome: success
   Resume: claude --resume abc123def456...
```

## 示例对话

### 示例 1: 时间范围查询

**用户**: "昨天做了什么"

**Claude 的思考过程**:
1. 理解 "昨天" = 2026-02-16（相对于今天 2026-02-17）
2. 这是时间范围查询，不是关键词搜索
3. 执行: `csa search "" --since yesterday`

**执行**:
```bash
csa search "" --since yesterday
```

### 示例 2: 关键词搜索

**用户**: "找 authentication 的会话"

**Claude 的思考过程**:
1. 理解这是关键词搜索
2. 执行: `csa search "authentication"`

**执行**:
```bash
csa search "authentication" --limit 5
```

### 示例 3: 时间 + 项目过滤

**用户**: "本周的 analyzer 项目工作"

**Claude 的思考过程**:
1. 理解 "本周" = 最近 7 天
2. 理解 "analyzer 项目" = 需要筛选项目路径
3. 先按时间列出，再筛选项目

**执行**:
```bash
csa search "analyzer" --since 7days --limit 10
```

### 示例 4: 继续之前的工作

**用户**: "继续之前的数据库迁移工作"

**Claude 的思考过程**:
1. 理解这是关键词搜索
2. 搜索 "数据库迁移" 或 "database migration"

**执行**:
```bash
csa search "数据库迁移 migration" --limit 5
```

## 工作流程

```
用户查询
    ↓
Claude 理解意图
    ↓
选择合适的工具和参数
    ↓
执行搜索命令
    ↓
返回结果 + Resume 命令
    ↓
用户复制 claude --resume <ID>
```

## 注意事项

1. **Session ID 是关键**：始终提供完整的 Session ID，用户需要用它来恢复会话
2. **时间格式**：支持 `YYYY-MM-DD` 或相对日期如 `yesterday`, `7days`
3. **中英文**：搜索支持中英文关键词
4. **空查询**：`csa search ""` 会列出所有会话（配合 `--since`/`--until` 使用）
