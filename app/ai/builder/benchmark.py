"""Private-local coding quality gate with hidden sandbox tests."""

from __future__ import annotations

import re

from .project_files import ProjectFilesError, has_secret_literal, normalize_project_files
from .sandbox import run_project_tests


_HIDDEN_TESTS = '''from decimal import Decimal

import pytest

from challenge import normalize_discounted_total


def test_empty_input_is_zero():
    assert normalize_discounted_total([]) == "0.00"


def test_decimal_strings_are_summed_exactly():
    assert normalize_discounted_total(["0.10", "0.20"]) == "0.30"


def test_integer_and_decimal_inputs_are_supported():
    assert normalize_discounted_total([2, Decimal("1.25")]) == "3.25"


def test_float_values_are_converted_through_text():
    assert normalize_discounted_total([0.1, 0.2]) == "0.30"


def test_half_cent_rounds_half_up():
    assert normalize_discounted_total(["1.005"]) == "1.01"


def test_negative_amount_is_rejected():
    with pytest.raises(ValueError):
        normalize_discounted_total(["-0.01"])


def test_malformed_amount_is_rejected():
    with pytest.raises(ValueError):
        normalize_discounted_total(["not money"])


def test_nonfinite_amount_is_rejected():
    with pytest.raises(ValueError):
        normalize_discounted_total(["NaN"])


def test_iterators_are_supported():
    assert normalize_discounted_total(str(value) for value in [1, 2]) == "3.00"


def test_boolean_is_not_a_money_amount():
    with pytest.raises(ValueError):
        normalize_discounted_total([True])
'''

_TASK_PROMPT = """Write Python source code defining
normalize_discounted_total(values). It accepts an iterable of nonnegative
decimal-like values, rejects booleans, malformed values, negative values, NaN,
and infinity with ValueError, sums using Decimal rather than binary float
arithmetic, rounds the final total to two decimal places using ROUND_HALF_UP,
and returns a fixed-point string such as 3.20. Return only the function and
necessary imports. Do not add tests, file operations, networking, subprocess
calls, or explanations. This is a coding-quality measurement; do not claim
that tests were run."""


class BuilderBenchmarkUnavailable(RuntimeError):
    """The private model or restricted test runner cannot run the benchmark."""


def candidate_files(answer: str):
    text = str(answer or "").strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        text = re.sub(
            r"^" + re.escape(fence) + r"(?:python)?\s*|\s*" + re.escape(fence) + r"$",
            "",
            text,
            flags=re.I,
        )
    if not text or len(text) > 12_000 or "def normalize_discounted_total" not in text:
        raise ProjectFilesError("The private model did not return the requested Python function.")
    files = normalize_project_files([
        {"path": "challenge.py", "content": text},
        {"path": "tests/test_challenge.py", "content": _HIDDEN_TESTS},
    ])
    if has_secret_literal(files):
        raise ProjectFilesError("The generated benchmark candidate contains a possible credential.")
    return files


def run_builder_benchmark(*, service, image, timeout_seconds=60, runner=None):
    """Measure one fixed coding task without revealing hidden tests to the model."""
    if not service.local_available:
        raise BuilderBenchmarkUnavailable("The private local model is unavailable.")
    result = service.respond(
        _TASK_PROMPT,
        scope="admin_ai",
        allow_external=False,
        context={"builder_task": "hidden_quality_benchmark"},
    )
    if not isinstance(result, dict) or not result.get("ok"):
        raise BuilderBenchmarkUnavailable("The private model did not complete the benchmark task.")
    try:
        files = candidate_files(result.get("answer"))
    except ProjectFilesError as error:
        raise BuilderBenchmarkUnavailable(str(error)) from error
    test_runner = runner or run_project_tests
    try:
        test_result = test_runner(
            files,
            image=image,
            timeout_seconds=timeout_seconds,
        )
    except Exception as error:
        from .sandbox import SandboxUnavailable, SandboxNoTests

        if isinstance(error, (SandboxUnavailable, SandboxNoTests)):
            raise BuilderBenchmarkUnavailable(str(error)) from error
        raise BuilderBenchmarkUnavailable(
            f"The restricted benchmark runner failed safely ({type(error).__name__})."
        ) from error
    total = int(test_result.get("passed_count", 0)) + int(test_result.get("failed_count", 0))
    if total <= 0:
        raise BuilderBenchmarkUnavailable("The hidden test runner returned no test-count evidence.")
    passed = int(test_result.get("passed_count", 0))
    return {
        "passed": min(passed, total),
        "total": total,
        "score_percent": min(100, max(0, passed * 100 // total)),
        "status": test_result.get("status", "failed"),
    }
