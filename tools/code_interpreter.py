"""Code Interpreter Tool — NL → code generation + sandboxed execution + auto-fix."""

import io
import re
import sys
import traceback
from typing import Any

from langchain_core.tools import tool

from prompts.examples import CODE_GEN_EXAMPLES
from prompts.templates import CODE_GEN_TEMPLATE, FIX_TEMPLATE

SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "ascii": ascii,
    "bin": bin, "bool": bool, "bytes": bytes, "chr": chr,
    "complex": complex, "dict": dict, "divmod": divmod,
    "enumerate": enumerate, "filter": filter, "float": float,
    "format": format, "frozenset": frozenset, "getattr": getattr,
    "hasattr": hasattr, "hash": hash, "hex": hex, "int": int,
    "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "next": next, "object": object, "oct": oct, "ord": ord,
    "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip, "Exception": Exception,
    "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "IndexError": IndexError,
    "StopIteration": StopIteration, "AssertionError": AssertionError,
    "ImportError": ImportError, "AttributeError": AttributeError,
    "ZeroDivisionError": ZeroDivisionError,
}


def _extract_code(text: str) -> str:
    """Extract Python code from markdown code blocks or raw text."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _execute_code(code: str) -> dict[str, str]:
    """Execute code in a sandboxed environment, capture stdout/stderr."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout_capture, stderr_capture
    result = {"stdout": "", "stderr": "", "exception": None}
    try:
        exec(code, {"__builtins__": SAFE_BUILTINS, "__name__": "__main__"})
        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()
    except Exception:
        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()
        result["exception"] = traceback.format_exc()
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    return result


def _build_few_shot_prompt() -> str:
    """Build few-shot examples string for code generation."""
    parts = []
    for i, ex in enumerate(CODE_GEN_EXAMPLES, 1):
        parts.append(f"--- 示例 {i} ---")
        parts.append(f"需求: {ex['user_request']}")
        parts.append(f"输出代码:\n```python\n{ex['output']['content']}\n```")
    return "\n".join(parts)


def generate_and_run(user_request: str, llm) -> dict[str, Any]:
    """Generate Python code from a natural language request and execute it.

    Retries up to 2 times on execution failure, feeding errors back to the LLM.
    """
    few_shot = _build_few_shot_prompt()
    full_prompt = (
        f"以下是代码生成的 few-shot 示例，请学习其风格和输出格式：\n{few_shot}\n\n"
        + CODE_GEN_TEMPLATE.format(user_request=user_request)
    )

    for attempt in range(3):
        response = llm.invoke(full_prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        code = _extract_code(raw)

        exec_result = _execute_code(code)

        if exec_result["exception"] is None:
            return {
                "type": "code",
                "status": "success",
                "content": code,
                "metadata": {
                    "stdout": exec_result["stdout"],
                    "attempts": attempt + 1,
                },
            }

        if attempt < 2:
            full_prompt = FIX_TEMPLATE.format(
                code=code, error=exec_result["exception"]
            )

    return {
        "type": "code",
        "status": "error",
        "content": code,
        "metadata": {
            "stdout": exec_result["stdout"],
            "stderr": exec_result["stderr"],
            "exception": exec_result["exception"],
            "attempts": 3,
        },
    }


@tool
def code_interpreter(user_request: str) -> str:
    """根据自然语言描述生成 Python 代码并执行。

    适用场景：
    - 实现一个具体的函数或算法
    - 数据处理脚本
    - 单元测试生成

    参数:
        user_request: 用自然语言描述的功能需求，越具体越好

    返回: 生成的代码、执行结果、是否成功
    """
    from agent import get_llm

    llm = get_llm()
    result = generate_and_run(user_request, llm)

    if result["status"] == "success":
        return (
            f"✅ 代码生成成功（第 {result['metadata']['attempts']} 次尝试）\n\n"
            f"```python\n{result['content']}\n```\n\n"
            f"执行输出:\n{result['metadata']['stdout']}"
        )
    return (
        f"❌ 代码执行失败（已尝试 3 次修正）\n\n"
        f"最后生成的代码:\n```python\n{result['content']}\n```\n\n"
        f"错误信息:\n{result['metadata']['exception']}"
    )
