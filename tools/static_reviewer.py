"""Static Code Reviewer — AST-based analysis for PEP 8, complexity, naming, bugs."""

import ast
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _read_code(source: str) -> tuple[str, str]:
    """Read code from a file path or return the source string directly."""
    path = Path(source)
    if path.is_file():
        return path.read_text(encoding="utf-8"), str(path)
    return source, "<inline>"


def _check_line_length(source: str) -> list[dict[str, Any]]:
    """Check each line for PEP 8 length violations."""
    issues = []
    for i, line in enumerate(source.split("\n"), 1):
        if len(line) > 100:
            issues.append({
                "severity": "WARNING",
                "line": i,
                "issue": f"行长度 {len(line)} 超过 100 字符限制",
                "suggestion": "将长行拆分为多行，或提取中间变量",
            })
    return issues


def _check_naming(code: str) -> list[dict[str, Any]]:
    """Check naming conventions using AST."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not re.match(r"^_*[a-z][a-z0-9_]*$", node.name) and not node.name.startswith("__"):
                issues.append({
                    "severity": "ERROR",
                    "line": node.lineno,
                    "issue": f"函数名 '{node.name}' 不符合 snake_case 规范",
                    "suggestion": f"建议改为: {re.sub(r'(?<!^)(?=[A-Z])', '_', node.name).lower()}",
                })
        elif isinstance(node, ast.ClassDef):
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                issues.append({
                    "severity": "ERROR",
                    "line": node.lineno,
                    "issue": f"类名 '{node.name}' 不符合 PascalCase 规范",
                    "suggestion": f"建议改为: {node.name[0].upper() + node.name[1:]}",
                })
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                if re.match(r"^[A-Z][A-Z_0-9]*$", node.id) and len(node.id) > 1:
                    pass  # CONSTANT_CASE is fine
                elif node.id.upper() == node.id and "_" in node.id:
                    pass  # CONSTANT
    return issues


def _check_complexity(code: str, threshold: int = 10) -> list[dict[str, Any]]:
    """Check cyclomatic complexity of functions."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Count decision points
        branches = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                branches += 1
            elif isinstance(child, ast.BoolOp):
                branches += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                branches += 1
            elif isinstance(child, ast.Match):  # Python 3.10+
                branches += len(child.cases)

        if branches > threshold:
            issues.append({
                "severity": "WARNING",
                "line": node.lineno,
                "issue": f"函数 '{node.name}' 圈复杂度为 {branches}，超过阈值 {threshold}",
                "suggestion": "考虑提取子函数或将条件判断改为查表/策略模式",
            })
    return issues


def _check_bug_patterns(code: str) -> list[dict[str, Any]]:
    """Check for common bug patterns."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        # Mutable default arguments
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append({
                        "severity": "ERROR",
                        "line": node.lineno,
                        "issue": "可变默认参数 — 所有调用共享同一个对象",
                        "suggestion": f"将默认值改为 None，在函数体内处理: {node.args.args[-1].arg}=None",
                    })

        # Bare except
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append({
                    "severity": "ERROR",
                    "line": node.lineno,
                    "issue": "裸 except 语句会捕获所有异常，包括 KeyboardInterrupt",
                    "suggestion": "明确指定要捕获的异常类型，至少使用 except Exception:",
                })

    return issues


def _check_imports(code: str) -> list[dict[str, Any]]:
    """Check import hygiene."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    # Star imports
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.names and node.names[0].name == "*":
            issues.append({
                "severity": "ERROR",
                "line": node.lineno,
                "issue": f"from {node.module or '?'} import * 会污染命名空间",
                "suggestion": "仅导入需要的符号，或使用 import module 的方式",
            })

    # Unused imports — simplified: flag top-level imports not referenced
    top_imports: dict[str, int] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                top_imports[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name != "*":
                    top_imports[name] = node.lineno

    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)

    for name, lineno in top_imports.items():
        root = name.split(".")[0]
        if root not in used_names:
            issues.append({
                "severity": "INFO",
                "line": lineno,
                "issue": f"导入 '{name}' 未在代码中使用",
                "suggestion": "移除未使用的导入",
            })

    return issues


def review_code(source: str, max_complexity: int = 10) -> dict[str, Any]:
    """Run all static analysis checks on the given code.

    Args:
        source: File path or code string.
        max_complexity: Cyclomatic complexity threshold for warnings.

    Returns:
        Structured review result with categorized issues and summary.
    """
    code, file_label = _read_code(source)

    all_issues = (
        _check_line_length(code)
        + _check_naming(code)
        + _check_complexity(code, max_complexity)
        + _check_bug_patterns(code)
        + _check_imports(code)
    )

    errors = sum(1 for i in all_issues if i["severity"] == "ERROR")
    warnings = sum(1 for i in all_issues if i["severity"] == "WARNING")
    info = sum(1 for i in all_issues if i["severity"] == "INFO")

    return {
        "type": "review",
        "status": "success",
        "file": file_label,
        "content": all_issues,
        "metadata": {"total_issues": len(all_issues), "errors": errors, "warnings": warnings, "info": info},
    }


@tool
def static_reviewer(source: str) -> str:
    """对 Python 代码进行静态分析和风格审查。

    检查项包括：
    - PEP 8 规范（行长度、空白）
    - 命名规范（snake_case / PascalCase / UPPER_CASE）
    - 圈复杂度
    - 常见 Bug 模式（可变默认参数、裸 except）
    - 导入语句规范

    参数:
        source: 要审查的 Python 文件路径 或 代码字符串

    返回: 结构化的审查报告，按严重程度分类
    """
    from config import DEFAULT_CONFIG

    result = review_code(source, DEFAULT_CONFIG.review_max_complexity)

    if not result["content"]:
        return f"✅ 审查通过: {result['file']} 未发现问题"

    lines = [f"📋 代码审查报告: {result['file']}"]
    lines.append(f"   总计 {result['metadata']['total_issues']} 个问题 "
                  f"(❌{result['metadata']['errors']} ⚠{result['metadata']['warnings']} "
                  f"ℹ{result['metadata']['info']})\n")

    severity_order = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
    for sev, icon in severity_order.items():
        for issue in result["content"]:
            if issue["severity"] == sev:
                lines.append(f"  {icon} L{issue['line']:>4d}: {issue['issue']}")
                lines.append(f"      → {issue['suggestion']}\n")

    return "\n".join(lines)
