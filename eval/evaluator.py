"""Code generation evaluator — measures first-attempt runnable rate.

Usage:
    python -m eval.evaluator          # Full benchmark (100 cases)
    python -m eval.evaluator --quick  # Quick check (10 random cases)
    python -m eval.evaluator --category recursion  # Single category
    python -m eval.evaluator --report report.json  # Save detailed report
"""

import argparse
import io
import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.test_cases import BENCHMARK_CASES, CATEGORY_STATS

# Fix UnicodeEncodeError on Windows GBK terminals
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluator")


class CodeGenEvaluator:
    """Runs the benchmark and computes the first-attempt runnable rate."""

    def __init__(self, llm=None, config: dict | None = None):
        """Initialize the evaluator.

        Args:
            llm: LangChain LLM instance. If None, uses the project's get_llm().
            config: Dict with keys: max_cases, categories, random_seed, save_report.
        """
        self.config = config or {}
        self._llm = llm
        self.results: list[dict[str, Any]] = []
        self.stats: dict[str, Any] = {}

    @property
    def llm(self):
        if self._llm is None:
            # Lazy import to avoid circular dependency
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from agent import get_llm

            self._llm = get_llm()
        return self._llm

    # ------------------------------------------------------------------
    # Core evaluation logic
    # ------------------------------------------------------------------

    def evaluate_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Run a single benchmark case and return detailed results.

        Returns a dict with:
            - case_id, category, subcategory
            - status: "success" | "syntax_error" | "runtime_error" | "timeout" | "no_code"
            - code: the generated code (if any)
            - attempt: always 1 for first-attempt evaluation
            - error: error message (if failed)
            - duration_ms: generation + execution time
        """
        from tools.code_interpreter import _execute_code, _extract_code

        # Build the prompt — same as the agent would use, but for first-attempt only
        from prompts.templates import CODE_GEN_TEMPLATE
        from prompts.examples import CODE_GEN_EXAMPLES

        # Few-shot context
        few_shot_parts = []
        for i, ex in enumerate(CODE_GEN_EXAMPLES, 1):
            few_shot_parts.append(f"--- 示例 {i} ---")
            few_shot_parts.append(f"需求: {ex['user_request']}")
            few_shot_parts.append(f"输出代码:\n```python\n{ex['output']['content']}\n```")

        full_prompt = (
            f"以下是代码生成的 few-shot 示例，请学习其风格和输出格式：\n"
            + "\n".join(few_shot_parts)
            + "\n\n"
            + CODE_GEN_TEMPLATE.format(user_request=case["user_request"])
        )

        start = time.perf_counter()

        try:
            response = self.llm.invoke(full_prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            if isinstance(raw, list):
                raw = "".join(
                    block.get("text", "") if isinstance(block, dict) and block.get("type") != "thinking" else ""
                    for block in raw
                )
            code = _extract_code(raw)
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            return {
                "case_id": case["id"],
                "category": case["category"],
                "subcategory": case["subcategory"],
                "user_request": case["user_request"],
                "status": "no_code",
                "code": "",
                "attempt": 1,
                "error": f"LLM invocation failed: {exc}",
                "duration_ms": round(duration, 1),
            }

        if not code or len(code.strip()) < 10:
            duration = (time.perf_counter() - start) * 1000
            return {
                "case_id": case["id"],
                "category": case["category"],
                "subcategory": case["subcategory"],
                "user_request": case["user_request"],
                "status": "no_code",
                "code": code,
                "attempt": 1,
                "error": "No code block found in LLM response",
                "duration_ms": round(duration, 1),
            }

        # ---- First-attempt execution (no retries) ----
        exec_result = _execute_code(code)

        duration = (time.perf_counter() - start) * 1000

        if exec_result["exception"] is None:
            status = "success"
            error = None
        elif "SyntaxError" in (exec_result["exception"] or ""):
            status = "syntax_error"
            error = exec_result["exception"]
        else:
            status = "runtime_error"
            error = exec_result["exception"]

        # Pattern check
        missing_patterns = []
        for pattern in case.get("expected_patterns", []):
            if pattern not in code:
                missing_patterns.append(pattern)

        return {
            "case_id": case["id"],
            "category": case["category"],
            "subcategory": case["subcategory"],
            "user_request": case["user_request"],
            "status": status,
            "code": code,
            "attempt": 1,
            "error": error,
            "missing_patterns": missing_patterns,
            "exec_stdout": exec_result["stdout"],
            "duration_ms": round(duration, 1),
        }

    # ------------------------------------------------------------------
    # Benchmark runner
    # ------------------------------------------------------------------

    def run_benchmark(
        self,
        cases: list[dict[str, Any]] | None = None,
        categories: list[str] | None = None,
        max_cases: int | None = None,
        random_seed: int = 42,
        progress_callback=None,
    ) -> dict[str, Any]:
        """Run the full benchmark.

        Args:
            cases: Custom case list. Uses BENCHMARK_CASES if None.
            categories: Filter to specific categories (e.g. ["basic", "recursion"]).
            max_cases: Limit number of cases (randomly sampled).
            random_seed: Seed for reproducible sampling.
            progress_callback: Called after each case with (index, total, result).

        Returns:
            Aggregated stats dict with per-category breakdown.
        """
        all_cases = cases or BENCHMARK_CASES

        if categories:
            all_cases = [c for c in all_cases if c["category"] in categories]

        if max_cases and max_cases < len(all_cases):
            rng = random.Random(random_seed)
            all_cases = sorted(rng.sample(all_cases, max_cases), key=lambda c: c["id"])

        logger.info("Starting benchmark: %d cases", len(all_cases))
        self.results = []

        for idx, case in enumerate(all_cases):
            logger.info("[%d/%d] %s: %s", idx + 1, len(all_cases), case["id"], case["user_request"][:50])
            result = self.evaluate_case(case)
            self.results.append(result)
            icon = "✅" if result["status"] == "success" else "❌"
            logger.info("  %s %s (%.0fms)", icon, result["status"], result["duration_ms"])
            if progress_callback:
                progress_callback(idx + 1, len(all_cases), result)

        self._compute_stats()
        return self.stats

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _compute_stats(self) -> None:
        """Compute aggregate statistics from results."""
        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "success")
        syntax_errors = sum(1 for r in self.results if r["status"] == "syntax_error")
        runtime_errors = sum(1 for r in self.results if r["status"] == "runtime_error")
        no_code = sum(1 for r in self.results if r["status"] == "no_code")

        avg_duration = (
            sum(r["duration_ms"] for r in self.results) / total if total else 0
        )

        # Per-category breakdown
        by_category: dict[str, dict[str, Any]] = {}
        for r in self.results:
            cat = r["category"]
            if cat not in by_category:
                by_category[cat] = {"total": 0, "success": 0, "syntax_error": 0, "runtime_error": 0, "no_code": 0}
            by_category[cat]["total"] += 1
            by_category[cat][r["status"]] += 1

        for cat, stats in by_category.items():
            stats["runnable_rate"] = round(
                stats["success"] / stats["total"] * 100, 1
            ) if stats["total"] else 0

        self.stats = {
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cases": total,
                "categories": list(by_category.keys()),
            },
            "overall": {
                "total": total,
                "success": success,
                "syntax_error": syntax_errors,
                "runtime_error": runtime_errors,
                "no_code": no_code,
                "runnable_rate": round(success / total * 100, 1) if total else 0,
                "avg_duration_ms": round(avg_duration, 1),
            },
            "by_category": by_category,
            "details": self.results,
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print a formatted benchmark report to stdout."""
        if not self.stats:
            print("No benchmark data. Run run_benchmark() first.")
            return

        overall = self.stats["overall"]
        meta = self.stats["meta"]

        print("\n" + "=" * 70)
        print("  📊 代码生成评估报告 — 首次生成可运行率")
        print("=" * 70)
        print(f"  🕐 时间:     {meta['timestamp']}")
        print(f"  📝 总用例数: {overall['total']}")
        print(f"  📂 分类数:   {len(meta['categories'])} ({', '.join(meta['categories'])})")
        print("-" * 70)
        print(f"  ✅ 可直接运行: {overall['success']:>4d}  ({overall['runnable_rate']}%)")
        print(f"  ❌ 语法错误:   {overall['syntax_error']:>4d}")
        print(f"  ⚠️  运行时错误: {overall['runtime_error']:>4d}")
        print(f"  🔇 无输出:     {overall['no_code']:>4d}")
        print(f"  ⏱️  平均耗时:   {overall['avg_duration_ms']:.0f}ms")
        print("-" * 70)

        # Category breakdown
        print("\n  📂 按分类统计:")
        print(f"  {'分类':<16} {'总数':>5} {'成功':>5} {'可运行率':>9}")
        print("  " + "-" * 38)
        for cat, stats in sorted(self.stats["by_category"].items()):
            label = CATEGORY_STATS.get(cat, {}).get("label", cat)
            print(
                f"  {label:<16} {stats['total']:>5} {stats['success']:>5} "
                f"{stats['runnable_rate']:>8.1f}%"
            )
        print("=" * 70 + "\n")

    def save_report(self, path: str) -> None:
        """Save the full report (including per-case details) to a JSON file."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(self.stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Report saved to %s", out.resolve())


# ═══════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════

def run_benchmark(
    categories: list[str] | None = None,
    max_cases: int | None = None,
    random_seed: int = 42,
    report_path: str | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """Convenience function for running the benchmark programmatically."""
    if quick:
        max_cases = max_cases or 10
        if not categories:
            categories = None  # sample from all

    evaluator = CodeGenEvaluator()
    stats = evaluator.run_benchmark(
        categories=categories,
        max_cases=max_cases,
        random_seed=random_seed,
    )
    evaluator.print_report()

    if report_path:
        evaluator.save_report(report_path)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Code Agent — 代码生成评估基准",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(CATEGORY_STATS.keys()),
        action="append",
        dest="categories",
        help="限定评估分类（可重复指定）",
    )
    parser.add_argument(
        "--max-cases", "-n",
        type=int, default=0,
        help="最大评估用例数（0 = 全部）",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="快速评估模式（随机 10 题）",
    )
    parser.add_argument(
        "--seed",
        type=int, default=42,
        help="随机种子（默认 42）",
    )
    parser.add_argument(
        "--report", "-o",
        default=None,
        help="保存详细报告到 JSON 文件",
    )

    args = parser.parse_args()

    max_cases = args.max_cases if args.max_cases > 0 else None
    if args.quick and max_cases is None:
        max_cases = 10

    run_benchmark(
        categories=args.categories,
        max_cases=max_cases,
        random_seed=args.seed,
        report_path=args.report,
        quick=args.quick,
    )


if __name__ == "__main__":
    main()
