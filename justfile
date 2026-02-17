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

# ========== 完整工作流 ==========

# 快速检查 (日常开发)
quick: fmt check
    @echo "✅ Quick check passed"

# 完整检查 (提交前)
full: check security test
    @echo "✅ Full check passed"

# CI/CD 流水线
ci: fmt check security test
    @echo "✅ CI 检查通过"

# ========== 运行 ==========

# 运行 CLI
run *ARGS:
    uv run csa {{ARGS}}

# 搜索会话
search query:
    uv run csa search "{{query}}"

# 分析会话文件
analyze file:
    uv run csa analyze {{file}}
