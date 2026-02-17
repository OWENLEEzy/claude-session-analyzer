# Claude Session Analyzer - 开发工作流
# 安装 just: brew install just

# 默认：显示帮助
default:
    @just --list

# ========== 开发环境 ==========

# 安装依赖
install:
    uv sync

# 添加依赖
add package:
    uv add {{package}}

# 添加开发依赖
add-dev package:
    uv add --dev {{package}}

# ========== 代码质量 ==========

# 快速检查 (lint + format + mypy)
check:
    uv run ruff check .
    uv run ruff format . --check
    uv run mypy analyzer/

# 格式化代码
fmt:
    uv run ruff format .
    uv run ruff check . --fix

# 类型检查
typecheck:
    uv run mypy analyzer/

# 安全扫描
security:
    uv run bandit -r analyzer/

# 死代码检测
deadcode:
    uv run vulture analyzer/

# ========== 测试 ==========

# 运行测试
test:
    uv run pytest tests/ -v

# 运行测试 + 覆盖率
coverage:
    uv run pytest tests/ --cov=analyzer --cov-report=term-missing

# 变异测试 (检查测试质量)
mutate *ARGS:
    uv run mutmut run analyzer/ {{ARGS}}

# API 属性测试 (需要 HTTP API)
api schema_url:
    @echo "🌐 Schemathesis API 测试"
    uv run schemathesis run {{schema_url}} --base-url http://localhost:8000

# ========== 完整工作流 ==========

# 快速检查 (日常开发)
quick:
    @./scripts/quality-check.sh quick

# 完整检查 (提交前)
full:
    @./scripts/quality-check.sh full

# CI/CD 流水线
ci: fmt check security test
    @echo "✅ CI 检查通过"

# ========== 运行 ==========

# 运行 CLI
run *ARGS:
    uv run csa {{ARGS}}

# 运行 MCP Server
mcp:
    uv run csa-mcp

# 演示智能搜索
demo:
    @uv run python3 -c "\
from analyzer import SmartSearch, MockMCPClient, SearchResult; \
s = object.__new__(SmartSearch); \
s.use_mock = True; \
s.intent_analyzer = None; \
s.mcp_client = MockMCPClient([\
    SearchResult('s1', '/p/auth', '用户认证', similarity=0.9),\
    SearchResult('s2', '/p/api', 'JWT处理', similarity=0.8),\
]); \
s.reranker = __import__('analyzer.reranker', fromlist=['ResultReranker']).ResultReranker(); \
r = s.search('继续做认证功能'); \
print(f'查询: {r.query}'); \
print(f'概念: {r.intent.concepts}'); \
print('✅ 搜索正常');"
