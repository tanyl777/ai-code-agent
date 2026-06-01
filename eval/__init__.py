"""Evaluation framework for the AI Code Agent.

Provides a 100-case benchmark dataset and an evaluator that measures
the core metric: "首次生成可运行率" (first-attempt runnable rate).
"""

from eval.evaluator import CodeGenEvaluator, run_benchmark
from eval.test_cases import BENCHMARK_CASES, CATEGORY_STATS

__all__ = ["CodeGenEvaluator", "run_benchmark", "BENCHMARK_CASES", "CATEGORY_STATS"]
