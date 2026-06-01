"""Git Commit Message Generator — analyzes git diff and generates Conventional Commits."""

import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _run_git(repo_path: str, args: list[str]) -> str:
    """Run a git command and return its stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True, text=True, encoding="utf-8",
        )
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def _run_git_full(repo_path: str, args: list[str]) -> tuple[int, str, str]:
    """Run git command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True, text=True, encoding="utf-8",
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return 1, "", str(e)


def git_add(repo_path: str, files: list[str] | None = None) -> tuple[bool, str]:
    """Stage files for commit. If files is None, stages all changes (git add -A)."""
    args = ["add", "-A"] if files is None else ["add"] + files
    rc, stdout, stderr = _run_git_full(repo_path, args)
    return rc == 0, stderr or stdout


def git_commit_exec(repo_path: str, message: str) -> tuple[bool, str]:
    """Execute git commit with the given message."""
    rc, stdout, stderr = _run_git_full(repo_path, ["commit", "-m", message])
    return rc == 0, stdout or stderr


def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> tuple[bool, str]:
    """Push commits to remote. If branch is empty, pushes current branch."""
    args = ["push", remote]
    if branch:
        args.append(branch)
    rc, stdout, stderr = _run_git_full(repo_path, args)
    return rc == 0, stdout or stderr


def git_get_remote(repo_path: str) -> str:
    """Get the origin remote URL."""
    return _run_git(repo_path, ["remote", "get-url", "origin"]).strip()


def git_status(repo_path: str) -> str:
    """Get git status summary."""
    return _run_git(repo_path, ["status", "--short"])


def _get_diffs(repo_path: str) -> tuple[str, str]:
    """Get staged and unstaged diffs from the repository."""
    staged = _run_git(repo_path, ["diff", "--staged", "--unified=3"])
    unstaged = _run_git(repo_path, ["diff", "--unified=3"])
    return staged.strip(), unstaged.strip()


def _get_branch(repo_path: str) -> str:
    """Get the current branch name."""
    return _run_git(repo_path, ["branch", "--show-current"]).strip()


def _get_changed_files(repo_path: str) -> list[str]:
    """Get list of changed files (staged + unstaged)."""
    staged = _run_git(repo_path, ["diff", "--staged", "--name-only"]).strip().split("\n")
    unstaged = _run_git(repo_path, ["diff", "--name-only"]).strip().split("\n")
    return sorted(set([f for f in staged + unstaged if f]))


def _generate_commit_message(
    staged_diff: str, unstaged_diff: str, files: list[str], llm
) -> dict[str, Any]:
    """Use LLM to generate a Conventional Commits message from the diffs."""
    from prompts.examples import COMMIT_EXAMPLES
    from prompts.templates import COMMIT_TEMPLATE

    # Build few-shot context
    few_shot_parts = ["以下是 Conventional Commits 的 few-shot 示例："]
    for i, ex in enumerate(COMMIT_EXAMPLES, 1):
        msg = ex["output"]["content"]
        body = msg.get("body", "")
        entry = f"{msg['type']}({msg['scope']}): {msg['message']}"
        if body:
            entry += f"\n\n{body}"
        few_shot_parts.append(f"--- 示例 {i} ---\n{entry}")

    few_shot_text = "\n".join(few_shot_parts)

    truncated_staged = staged_diff[:4000] if staged_diff else "(无暂存变更)"
    truncated_unstaged = unstaged_diff[:4000] if unstaged_diff else "(无未暂存变更)"

    prompt = (
        f"{few_shot_text}\n\n"
        + COMMIT_TEMPLATE.format(
            staged_diff=truncated_staged,
            unstaged_diff=truncated_unstaged,
        )
    )

    response = llm.invoke(prompt)
    raw = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw, list):
        raw = "".join(
            block.get("text", "") if isinstance(block, dict) and block.get("type") != "thinking" else ""
            for block in raw
        )

    # Try to parse structured output from the LLM's JSON response
    import json
    try:
        # Extract JSON block
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data
    except (json.JSONDecodeError, AttributeError):
        pass

    return {"type": "unknown", "scope": "", "message": raw.strip()}


@tool
def git_commit(repo_path: str = ".") -> str:
    """分析 Git 仓库的暂存变更，生成符合 Conventional Commits 规范的提交信息。

    仅生成建议，不会自动提交。需要仓库中存在变更（已暂存或未暂存）。

    参数:
        repo_path: Git 仓库路径，默认为当前目录

    返回: 生成的 commit message 建议
    """
    from agent import get_llm

    repo = Path(repo_path).resolve()
    if not (repo / ".git").exists():
        return f"❌ 错误: '{repo}' 不是一个 Git 仓库"

    staged, unstaged = _get_diffs(str(repo))
    files = _get_changed_files(str(repo))
    branch = _get_branch(str(repo))

    if not staged and not unstaged:
        return "ℹ️ 当前仓库没有变更，无需生成 commit message"

    if not staged and unstaged:
        return (
            "⚠️ 没有暂存的变更。请先使用 git add 暂存要提交的文件。\n\n"
            f"未暂存的文件: {', '.join(files)}"
        )

    llm = get_llm()
    msg = _generate_commit_message(staged, unstaged, files, llm)

    lines = [
        f"📝 建议的 Commit Message (branch: {branch})\n",
        f"  {msg.get('type', '?')}({msg.get('scope', '?')}): {msg.get('message', msg.get('content', str(msg)))}",
    ]

    body = msg.get("body", "")
    if body:
        lines.append(f"\n{body}")

    lines.append(f"\n📁 涉及文件 ({len(files)}):")
    for f in files[:10]:
        lines.append(f"  - {f}")
    if len(files) > 10:
        lines.append(f"  ... 还有 {len(files) - 10} 个文件")

    lines.append("\n💡 如满意，执行: git commit -m \"...\"")
    return "\n".join(lines)
