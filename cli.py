#!/usr/bin/env python3
"""
AI 编程助手 Agent — 命令行入口

用法:
    python cli.py run "实现一个二分查找函数"      代码生成 + 执行
    python cli.py review src/utils.py            静态代码审查
    python cli.py commit                         生成 commit message
    python cli.py chat                           交互式多轮对话
"""

import argparse
import io
import json
import sys

# Fix UnicodeEncodeError on Windows GBK terminals
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agent import create_agent, reset_agent, run
from config import DEFAULT_CONFIG, AgentConfig, LLMConfig
from memory.session_memory import SessionMemory
from tools.code_interpreter import generate_and_run
from tools.static_reviewer import review_code
from tools.git_commit import _get_diffs, _generate_commit_message, _get_changed_files, _get_branch
from tools.test_generator import generate_and_test as generate_tests


def cmd_run(args: argparse.Namespace) -> None:
    """Handle 'run' subcommand — generate and execute code from NL."""
    from agent import get_llm

    llm = get_llm()
    result = generate_and_run(args.request, llm)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result["status"] == "success":
        print(f"✅ 代码生成成功（第 {result['metadata']['attempts']} 次尝试）\n")
        print(result["content"])
        if result["metadata"]["stdout"]:
            print(f"\n--- 执行输出 ---")
            print(result["metadata"]["stdout"])
    else:
        print(f"❌ 代码执行失败（已尝试 {result['metadata']['attempts']} 次修正）\n")
        print(result["content"])
        print(f"\n--- 错误信息 ---")
        print(result["metadata"]["exception"])


def cmd_review(args: argparse.Namespace) -> None:
    """Handle 'review' subcommand — static code analysis."""
    result = review_code(args.source, args.max_complexity)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not result["content"]:
        print(f"✅ 审查通过: {result['file']} 未发现问题")
        return

    print(f"📋 代码审查报告: {result['file']}")
    print(f"   总计 {result['metadata']['total_issues']} 个问题 "
          f"(❌{result['metadata']['errors']} ⚠{result['metadata']['warnings']} "
          f"ℹ{result['metadata']['info']})\n")

    severity_order = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
    for sev, icon in severity_order.items():
        for issue in result["content"]:
            if issue["severity"] == sev:
                print(f"  {icon} L{issue['line']:>4d}: {issue['issue']}")
                print(f"      → {issue['suggestion']}\n")


def cmd_commit(args: argparse.Namespace) -> None:
    """Handle 'commit' subcommand — generate Conventional Commits message."""
    from pathlib import Path
    from agent import get_llm

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"❌ 错误: '{repo}' 不是一个 Git 仓库")
        sys.exit(1)

    staged, unstaged = _get_diffs(str(repo))
    files = _get_changed_files(str(repo))
    branch = _get_branch(str(repo))

    if not staged and not unstaged:
        print("ℹ️ 当前仓库没有变更，无需生成 commit message")
        return

    if not staged and unstaged:
        print("⚠️ 没有暂存的变更。请先使用 git add 暂存要提交的文件。\n")
        print(f"未暂存的文件: {', '.join(files)}")
        return

    llm = get_llm()
    msg = _generate_commit_message(staged, unstaged, files, llm)

    if args.json:
        print(json.dumps(msg, ensure_ascii=False, indent=2))
        return

    print(f"📝 建议的 Commit Message (branch: {branch})\n")
    print(f"  {msg.get('type', '?')}({msg.get('scope', '?')}): {msg.get('message', msg.get('content', str(msg)))}")

    body = msg.get("body", "")
    if body:
        print(f"\n{body}")

    print(f"\n📁 涉及文件 ({len(files)}):")
    for f in files[:10]:
        print(f"  - {f}")
    if len(files) > 10:
        print(f"  ... 还有 {len(files) - 10} 个文件")

    print("\n💡 如满意，执行: git commit -m \"...\"")


def cmd_test(args: argparse.Namespace) -> None:
    """Handle 'test' subcommand — generate pytest unit tests for source code."""
    from pathlib import Path
    from agent import get_llm

    llm = get_llm()
    result = generate_tests(args.source, llm, max_retries=args.max_retries)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result["status"] == "success":
        print(f"✅ 测试生成成功（第 {result['metadata']['attempts']} 次尝试）\n")
        print(f"📁 源文件: {result['file']}")
        print(f"🧪 {result['metadata']['test_output']}\n")
        if args.output:
            Path(args.output).write_text(result["content"], encoding="utf-8")
            print(f"💾 测试代码已写入: {args.output}")
        else:
            print(result["content"])
    else:
        print(f"❌ 测试生成失败（已尝试 {result['metadata']['attempts']} 次修正）\n")
        print(f"📁 源文件: {result['file']}")
        print(f"🧪 {result['metadata'].get('test_output', '无')}")
        err = result['metadata'].get('test_stderr', '')
        if err:
            print(f"\n--- 错误详情 ---\n{err}")


def cmd_chat(args: argparse.Namespace) -> None:
    """Handle 'chat' subcommand — interactive multi-turn conversation."""
    import uuid

    print("🤖 AI 编程助手 (输入 'quit' 退出, 'clear' 清空记忆, 'history' 查看历史)\n")

    config = DEFAULT_CONFIG
    if args.model:
        config = AgentConfig(llm=LLMConfig(model=args.model))
    if args.api_key:
        config.llm.api_key = args.api_key

    thread_id = str(uuid.uuid4())[:8]
    from agent import set_thread_id
    set_thread_id(thread_id)

    create_agent(config)
    backup = SessionMemory(config.memory_file)

    print(f"📊 模型: {config.llm.model}  |  Thread: {thread_id}  |  "
          f"记忆: {'已加载' if len(backup) > 0 else '新会话'}\n")

    while True:
        try:
            user_input = input("👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("👋 再见!")
            break
        if user_input.lower() == "clear":
            reset_agent()
            backup.clear()
            print("🧹 记忆已清空\n")
            continue
        if user_input.lower() == "history":
            print(backup.get_context_summary(last_n=10))
            print()
            continue

        backup.add_user_message(user_input)
        print("🤖 助手: ", end="", flush=True)
        try:
            result = run(user_input)
            output = result.get("output", str(result))
            print(output)
            backup.add_ai_message(output)
            backup.save()
        except Exception as exc:
            print(f"⚠️ 出错了: {exc}")
        print()


def cmd_cache(args: argparse.Namespace) -> None:
    """Handle 'cache' subcommand — show or clear the LLM response cache."""
    from agent import cache_stats, clear_cache

    if args.clear:
        n = clear_cache(older_than=args.older_than)
        print(f"🧹 已清除 {n} 条缓存")
    else:
        stats = cache_stats()
        print(f"📦 LLM 响应缓存:")
        print(f"   条目数: {stats['entries']}")
        print(f"   大小:   {stats['size_kb']} KB")
        print(f"   目录:   {stats['directory']}")
        if stats['entries'] > 0:
            print(f"\n💡 执行 'python cli.py cache --clear' 清空缓存")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI 编程助手 Agent — 基于 LangChain ReAct + Claude/DeepSeek API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python cli.py run \"实现二分查找\"\n"
               "  python cli.py review app.py\n"
               "  python cli.py test src/utils.py\n"
               "  python cli.py commit .\n"
               "  python cli.py chat\n"
               "  python cli.py cache",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出（调试用）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run
    p_run = subparsers.add_parser("run", help="💻 自然语言 → 代码生成 + 沙箱执行 + 自动修正")
    p_run.add_argument("request", help="用自然语言描述的功能需求")
    p_run.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    p_run.set_defaults(func=cmd_run)

    # review
    p_review = subparsers.add_parser("review", help="🔍 AST 静态代码审查 (PEP8/命名/复杂度/Bug/导入)")
    p_review.add_argument("source", help="Python 文件路径 或 代码字符串")
    p_review.add_argument("--max-complexity", type=int, default=10, help="圈复杂度阈值 (默认: 10)")
    p_review.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    p_review.set_defaults(func=cmd_review)

    # test
    p_test = subparsers.add_parser("test", help="🧪 为 Python 代码生成 pytest 单元测试 + 自动验证")
    p_test.add_argument("source", help="Python 文件路径 或 代码字符串")
    p_test.add_argument("--max-retries", type=int, default=2, help="测试失败时最大修正次数 (默认: 2)")
    p_test.add_argument("--output", "-o", default=None, help="将生成的测试代码写入指定文件")
    p_test.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    p_test.set_defaults(func=cmd_test)

    # commit
    p_commit = subparsers.add_parser("commit", help="📝 分析 git diff → Conventional Commits 提交信息")
    p_commit.add_argument("repo", nargs="?", default=".", help="Git 仓库路径 (默认: 当前目录)")
    p_commit.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    p_commit.set_defaults(func=cmd_commit)

    # chat
    p_chat = subparsers.add_parser("chat", help="💬 交互式多轮对话 (带持久记忆)")
    p_chat.add_argument("--model", default=None, help="模型名称")
    p_chat.add_argument("--api-key", default=None, help="API Key (默认: 环境变量)")
    p_chat.set_defaults(func=cmd_chat)

    # cache
    p_cache = subparsers.add_parser("cache", help="📦 查看/清空 LLM 响应缓存")
    p_cache.add_argument("--clear", action="store_true", help="清空缓存")
    p_cache.add_argument("--older-than", type=int, default=0, help="仅清除 N 秒前的缓存")
    p_cache.set_defaults(func=cmd_cache)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
