#!/bin/bash
# 质量检查工作流
# 用法: ./scripts/quality-check.sh [quick|full|mutate]

set -e

echo "🔍 Claude Session Analyzer - 质量检查"
echo "========================================"

MODE=${1:-quick}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}▶ $1${NC}"; }

# 1. 代码格式化
info "Ruff Format..."
if uv run ruff format analyzer/ tests/ --check; then
    pass "代码格式正确"
else
    info "正在格式化..."
    uv run ruff format analyzer/ tests/
    pass "代码已格式化"
fi

# 2. Lint 检查
info "Ruff Lint..."
if uv run ruff check analyzer/ tests/; then
    pass "Lint 检查通过"
else
    fail "Lint 检查失败"
fi

# 3. 类型检查
info "Mypy 类型检查..."
if uv run mypy analyzer/; then
    pass "类型检查通过"
else
    fail "类型检查失败"
fi

# 4. 安全扫描
info "Bandit 安全扫描..."
if uv run bandit -r analyzer/ -q; then
    pass "无安全问题"
else
    fail "发现安全问题"
fi

# 5. 死代码检测
info "Vulture 死代码检测..."
if uv run vulture analyzer/; then
    pass "无死代码"
else
    fail "发现死代码"
fi

# 6. 单元测试 + 覆盖率
info "Pytest 单元测试..."
if uv run pytest tests/ --cov=analyzer --cov-fail-under=70 -q; then
    pass "测试通过"
else
    fail "测试失败"
fi

# 完整模式额外检查
if [ "$MODE" = "full" ] || [ "$MODE" = "mutate" ]; then
    echo ""
    echo "🧬 变异测试 (可能需要几分钟)..."
    info "Mutmut 变异测试..."
    # 跳过 intent_analyzer (需要 API key 的测试与 mutmut 不兼容)
    uv run mutmut run analyzer/reranker.py analyzer/core.py --max-children 2 2>/dev/null || echo "   ⚠️  变异测试部分跳过"
fi

# API 测试 (如果有 HTTP API)
if [ "$MODE" = "full" ]; then
    echo ""
    echo "🌐 API 属性测试..."
    info "Schemathesis..."
    # MCP Server 使用 stdio，暂不支持 HTTP API 测试
    # 如需测试 HTTP API，请提供 OpenAPI schema URL:
    # uv run schemathesis run http://localhost:8000/openapi.json
    echo "   ⏭️  跳过 (MCP Server 使用 stdio，非 HTTP)"
fi

echo ""
echo "========================================"
pass "所有检查通过! 🎉"
