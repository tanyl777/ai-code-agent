"""Test Generator Tool — generates pytest unit tests from Python source code."""

import io
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from prompts.examples import TEST_GEN_EXAMPLES
from prompts.templates import TEST_GEN_TEMPLATE, TEST_FIX_TEMPLATE


def _read_source(source: str) -> tuple[str, str]:
    """Read source code from a file path or return the string directly."""
    path = Path(source)
    if path.is_file():
        return path.read_text(encoding="utf-8"), str(path)
    return source, "<inline>"


def _extract_code(text: str) -> str:
    """Extract Python code from JSON response, markdown code blocks, or raw text."""
    import json as _json

    # --- Step 1: Strip markdown fences ---
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*\n?", "", clean)
        clean = re.sub(r"\n?```\s*$", "", clean)

    # --- Step 2: Try parsing as JSON ---
    try:
        data = _json.loads(clean)
        # Check all possible code keys
        for key in ("corrected_test_code", "corrected_test", "code", "content"):
            if key in data and isinstance(data[key], str):
                return data[key].strip()
    except (_json.JSONDecodeError, TypeError):
        pass

    # --- Step 3: Regex fallback for non-standard JSON (handles nested braces) ---
    for key in ("corrected_test_code", "corrected_test", "code"):
        # Extract JSON object containing the key using brace counting
        start = text.find(f'"{key}"')
        if start >= 0:
            # Find the enclosing { } using brace counting
            obj_start = text.rfind("{", 0, start)
            if obj_start >= 0:
                depth = 0
                obj_end = obj_start
                for i in range(obj_start, len(text)):
                    if text[i] == "{": depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            obj_end = i + 1
                            break
                try:
                    data = _json.loads(text[obj_start:obj_end])
                    if key in data and isinstance(data[key], str):
                        return data[key].strip()
                except (_json.JSONDecodeError, TypeError):
                    pass

    # --- Step 4: Markdown code blocks ---
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()


def _build_few_shot_prompt() -> str:
    """Build few-shot examples string for test generation."""
    parts = []
    for i, ex in enumerate(TEST_GEN_EXAMPLES, 1):
        parts.append(f"--- 示例 {i} ---")
        parts.append(f"源代码:\n```python\n{ex['source_code']}\n```")
        parts.append(f"生成的测试:\n```python\n{ex['output']['content']}\n```")
    return "\n".join(parts)


def _guess_module_name(test_code: str, source_code: str) -> str:
    """Guess the module name the test expects, based on import statements and source content.

    1. Parse import statements from test_code (e.g. ``from palindrome import ...``)
    2. Fall back to extracting a function/class name from source_code
    3. Final fallback: "source_module"
    """
    # Match "from <module> import ..." in test code
    import_match = re.findall(r"^from\s+(\w+)\s+import", test_code, re.MULTILINE)
    if import_match:
        # Filter out stdlib modules
        stdlib = {"os", "sys", "json", "re", "math", "time", "datetime", "collections",
                  "itertools", "functools", "typing", "io", "pathlib", "unittest", "pytest"}
        for name in import_match:
            if name not in stdlib:
                return name

    # Match "import <module>" in test code
    import_match2 = re.findall(r"^import\s+(\w+)", test_code, re.MULTILINE)
    if import_match2:
        stdlib = {"os", "sys", "json", "re", "math", "time", "datetime", "collections",
                  "itertools", "functools", "typing", "io", "pathlib", "unittest", "pytest"}
        for name in import_match2:
            if name not in stdlib:
                return name

    # Fall back to extracting function/class name from source
    func_match = re.findall(r"def\s+(\w+)", source_code)
    if func_match:
        # Use the first function name as a snake_case module name
        return re.sub(r"(?<!^)(?=[A-Z])", "_", func_match[0]).lower().replace("__", "_")

    class_match = re.findall(r"class\s+(\w+)", source_code)
    if class_match:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", class_match[0]).lower().replace("__", "_")

    return "source_module"


def _find_imported_modules(test_code: str, source_code: str = "") -> list[str]:
    """Find all non-stdlib module names imported in test_code.

    Used to create matching .py files so pytest can resolve imports even when
    the source file has a different filename than the expected module name.
    """
    stdlib = {
        "os", "sys", "json", "re", "math", "time", "datetime", "collections",
        "itertools", "functools", "typing", "io", "pathlib", "unittest", "pytest",
        "csv", "logging", "argparse", "subprocess", "tempfile", "shutil", "abc",
        "dataclasses", "enum", "textwrap", "hashlib", "random", "string",
    }
    modules = set()
    for m in re.findall(r"^from\s+(\w+)\s+import", test_code, re.MULTILINE):
        if m not in stdlib:
            modules.add(m)
    for m in re.findall(r"^import\s+(\w+)", test_code, re.MULTILINE):
        if m not in stdlib:
            modules.add(m)
    return list(modules)


def _run_pytest(test_code: str, source_code: str | None = None, source_file: str | None = None) -> dict[str, Any]:
    """Run pytest on the generated test code and return results.

    Creates a temporary directory with the test file and the source module
    (from source_file or inline source_code), then runs pytest --tb=short -q.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write the test file
        test_path = tmp / "test_generated.py"
        test_path.write_text(test_code, encoding="utf-8")

        # Create the source module so tests can import from it
        if source_file:
            src_path = Path(source_file)
            if src_path.is_file():
                # Copy with original name
                dest = tmp / src_path.name
                dest.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
                # Also create copies for any module name the test tries to import
                # (handles case where test imports "binary_search" but file is "01_binary_search.py")
                extra_names = _find_imported_modules(test_code, source_code)
                for name in extra_names:
                    alias_path = tmp / f"{name}.py"
                    if alias_path != dest and not alias_path.exists():
                        alias_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
        elif source_code:
            # Inline code: detect the module name the test is trying to import
            # and save the source under that name, falling back to source_module.py
            module_name = _guess_module_name(test_code, source_code)
            module_path = tmp / f"{module_name}.py"
            module_path.write_text(source_code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "--tb=short", "-q", "-v"],
                capture_output=True, text=True, cwd=str(tmp), timeout=30,
            )
            stdout = result.stdout
            stderr = result.stderr
            passed = result.returncode == 0
        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = "测试执行超时（30 秒）"
            passed = False
        except FileNotFoundError:
            return {
                "passed": None,
                "stdout": "",
                "stderr": "⚠️ pytest 未安装。请执行: pip install pytest",
                "summary": "pytest 不可用",
            }

        # Parse pytest summary line
        summary = ""
        for line in (stdout + stderr).split("\n"):
            if "passed" in line or "failed" in line or "error" in line:
                if "===" in line:
                    summary = line.strip()
                    break

        return {
            "passed": passed,
            "stdout": stdout,
            "stderr": stderr,
            "summary": summary or (stdout[-200:] if stdout else stderr[:200]),
        }


def generate_and_test(source: str, llm, max_retries: int = 2) -> dict[str, Any]:
    """Generate pytest tests for source code and validate by running them.

    Args:
        source: File path or code string to generate tests for.
        llm: LangChain LLM instance.
        max_retries: Maximum fix attempts on test failure (default 2 → 3 total attempts).

    Returns:
        Structured result with generated test code and execution results.
    """
    source_code, file_label = _read_source(source)

    few_shot = _build_few_shot_prompt()
    full_prompt = (
        f"以下是测试生成的 few-shot 示例，请学习其测试风格和覆盖模式：\n{few_shot}\n\n"
        + TEST_GEN_TEMPLATE.format(source_code=source_code)
    )

    for attempt in range(max_retries + 1):
        response = llm.invoke(full_prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        if isinstance(raw, list):
            raw = "".join(
                block.get("text", "") if isinstance(block, dict) and block.get("type") != "thinking" else ""
                for block in raw
            )
        test_code = _extract_code(raw)

        # Run the generated tests
        test_result = _run_pytest(
            test_code,
            source_code=source_code,
            source_file=source if Path(source).is_file() else None,
        )

        if test_result["passed"]:
            return {
                "type": "test",
                "status": "success",
                "content": test_code,
                "file": file_label,
                "metadata": {
                    "attempts": attempt + 1,
                    "test_output": test_result["summary"],
                },
            }

        if attempt < max_retries:
            full_prompt = TEST_FIX_TEMPLATE.format(
                test_code=test_code,
                error=test_result["stderr"] or test_result["stdout"],
            )

    return {
        "type": "test",
        "status": "error",
        "content": test_code,
        "file": file_label,
        "metadata": {
            "attempts": max_retries + 1,
            "test_output": test_result["summary"],
            "test_stderr": test_result["stderr"],
        },
    }


@tool
def test_generator(source: str) -> str:
    """为 Python 源代码生成 pytest 单元测试并自动执行验证。

    会生成覆盖以下场景的测试：
    - 基础功能（正常输入 → 期望输出）
    - 边界条件（空值、单元素、极值）
    - 异常情况（无效参数、类型错误）
    - 使用 @pytest.mark.parametrize 参数化

    参数:
        source: Python 文件路径 或 代码字符串

    返回: 生成的测试代码、pytest 执行结果、是否全部通过
    """
    from agent import get_llm

    llm = get_llm()
    result = generate_and_test(source, llm)

    if result["status"] == "success":
        return (
            f"✅ 测试生成成功（第 {result['metadata']['attempts']} 次尝试）\n\n"
            f"📁 源文件: {result['file']}\n"
            f"🧪 测试结果: {result['metadata']['test_output']}\n\n"
            f"```python\n{result['content']}\n```"
        )
    return (
        f"❌ 测试生成失败（已尝试 {result['metadata']['attempts']} 次修正）\n\n"
        f"📁 源文件: {result['file']}\n"
        f"🧪 测试结果: {result['metadata'].get('test_output', '无')}\n"
        f"错误详情:\n{result['metadata'].get('test_stderr', '无')}\n\n"
        f"最后生成的测试:\n```python\n{result['content']}\n```"
    )
