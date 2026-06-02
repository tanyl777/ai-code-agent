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


def _check_undefined_vars(code: str) -> list[dict[str, Any]]:
    """Detect variables that are used but never defined in scope."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        # Collect assigned names inside this function
        assigned = set()
        assigned.update(a.arg for a in node.args.args)  # parameters
        if node.args.vararg: assigned.add(node.args.vararg.arg)
        if node.args.kwarg: assigned.add(node.args.kwarg.arg)
        used = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    assigned.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    used.add(child.id)
            elif isinstance(child, ast.arg):
                assigned.add(child.arg)

        # Filter builtins
        builtins = {"print", "len", "range", "int", "str", "list", "dict", "set", "tuple",
                     "bool", "float", "abs", "max", "min", "sum", "sorted", "reversed",
                     "enumerate", "zip", "map", "filter", "isinstance", "issubclass",
                     "hasattr", "getattr", "type", "super", "Exception", "ValueError",
                     "TypeError", "True", "False", "None", "random", "time", "open"}
        undefined = used - assigned - builtins - {"self", "cls"}

        for name in sorted(undefined):
            # Find first use line
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load):
                    issues.append({
                        "severity": "ERROR",
                        "line": child.lineno,
                        "issue": f"变量 '{name}' 未定义（可能是拼写错误）",
                        "suggestion": f"检查 '{name}' 是否拼写正确，或是否忘记定义/导入",
                    })
                    break
    return issues


_COMMON_TYPOS = {
    "printf": "print",
    "warpper": "wrapper",
    "attemp": "attempt",
    "fumc": "func",
    "fucn": "func",
    "fucntion": "function",
    "retrun": "return",
    "improt": "import",
    "defualt": "default",
    "excepet": "except",
    "rasing": "raising",
    "__main__": None,  # special: check for _main_ mistake
}


def _check_common_typos(code: str) -> list[dict[str, Any]]:
    """Detect common variable name typos."""
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Check for _main_ instead of __main__
        if "name" in stripped and '"_main_"' in stripped:
            issues.append({
                "severity": "ERROR",
                "line": i,
                "issue": "使用了 '_main_' 而不是 '__main__'（双下划线）",
                "suggestion": "改为: if __name__ == '__main__'",
            })
        # Check for common typos in variable names
        import re
        for line_word in re.findall(r'\b\w+\b', stripped):
            if line_word in _COMMON_TYPOS and _COMMON_TYPOS[line_word] is not None:
                issues.append({
                    "severity": "ERROR",
                    "line": i,
                    "issue": f"疑似拼写错误: '{line_word}'，可能想写 '{_COMMON_TYPOS[line_word]}'",
                    "suggestion": f"将 '{line_word}' 改为 '{_COMMON_TYPOS[line_word]}'",
                })
                break  # one issue per line
    return issues


def _check_param_usage(code: str) -> list[dict[str, Any]]:
    """Detect parameter name mismatches (e.g., decorator using wrong param names)."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    # Get all function definitions and their parameter names
    func_params = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params = set()
            for a in node.args.args:
                params.add(a.arg)
            if node.args.vararg:
                params.add(node.args.vararg.arg)
            func_params[node.name] = params

    # Find decorator calls and check param names
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                caller = node.func.id
                if caller in func_params:
                    expected = func_params[caller]
                    for kw in node.keywords:
                        if kw.arg and kw.arg not in expected:
                            close = _closest_match(kw.arg, expected)
                            hint = f"，参数名不匹配。'{caller}' 定义的参数: {expected}"
                            if close:
                                hint += f"，可能想写 '{close}'"
                            issues.append({
                                "severity": "ERROR",
                                "line": node.lineno,
                                "issue": f"调用 '{caller}' 时使用了不存在的参数 '{kw.arg}'",
                                "suggestion": hint,
                            })

    # Also check variable usage consistency in functions
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        params = {a.arg for a in node.args.args}
        used_in_body = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                used_in_body.add(child.id)
        # Check if any used name is a near-miss of a parameter
        for used in used_in_body:
            for param in params:
                if _similar(used, param) and used != param:
                    issues.append({
                        "severity": "ERROR",
                        "line": node.lineno,
                        "issue": f"函数内使用了 '{used}'，但参数名是 '{param}'，可能是拼写错误",
                        "suggestion": f"将 '{used}' 改为 '{param}'，或检查变量来源",
                    })
                    break
    return issues


def _similar(a: str, b: str) -> bool:
    """Check if two strings are similar (one char off)."""
    if abs(len(a) - len(b)) > 1:
        return False
    # Simple edit distance check
    diffs = 0
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            diffs += 1
    diffs += abs(len(a) - len(b))
    return diffs <= 1


def _closest_match(target: str, candidates: set[str]) -> str | None:
    """Find the closest matching candidate string."""
    best, best_dist = None, 999
    for c in candidates:
        # Simple character overlap check
        common = sum(1 for ch in target if ch in c)
        if common > len(target) * 0.5 and common > best_dist:
            best, best_dist = c, common
    return best if best_dist > 0 else None


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
        + _check_undefined_vars(code)
        + _check_common_typos(code)
        + _check_param_usage(code)
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
