from app.ai.evaluation import AI_EVALUATION_CASES, _check_case, evaluate_ai


def test_benchmark_checks_math_multilingual_grounding_and_coding_markers():
    answers = {
        "math-multiplication": "FINAL: 323",
        "math-discount": "ছাড়=180 টাকা, শেষ দাম=1020 টাকা",
        "math-percentage-trap": "FINAL: 960 taka, net decrease 4%.",
        "bangla-understanding": "তৃতীয় সংখ্যাটি ১২।",
        "banglish-understanding": "Total 90 taka.",
        "coding-function-syntax": "```python\ndef count_even(numbers):\n    return sum(n % 2 == 0 for n in numbers)\n```",
        "coding-debugging": "This is a mutable default argument bug. Use None and create a new list.",
        "uncertainty-private-data": "I cannot verify private order or stock information.",
        "shopping-live-price-english": "I cannot verify that without a live catalog result.",
        "shopping-live-price-bangla": "বর্তমান ক্যাটালগ থেকে যাচাই করতে হবে।",
        "support-return-policy-banglish": (
            "Order data ekhane nei, tai I cannot verify. Order page ba support policy check korun."
        ),
    }

    report = evaluate_ai(lambda prompt: {
        "answer": answers[next(
            case.case_id for case in AI_EVALUATION_CASES if case.prompt == prompt
        )]
    })

    assert report["passed_count"] == len(AI_EVALUATION_CASES)
    assert report["failed_count"] == 0
    assert report["human_review_required"] is True
    assert all(result["passed"] for result in report["results"])
    assert "answer" not in report
    assert all("prompt" not in result for result in report["results"])


def test_benchmark_flags_wrong_math_syntax_and_unverified_claims():
    answers = {
        "math-multiplication": "FINAL: 1323",
        "coding-function-syntax": "```python\ndef count_even(:\n    return 0\n```",
        "uncertainty-private-data": "Your order is arriving tomorrow and stock is available.",
    }
    selected = [
        next(case for case in AI_EVALUATION_CASES if case.case_id == case_id)
        for case_id in answers
    ]

    failures = {
        case.case_id: _check_case(case, answers[case.case_id])
        for case in selected
    }

    assert failures["math-multiplication"] == ["missing_expected_answer_marker"]
    assert "invalid_python_syntax" in failures["coding-function-syntax"]
    assert failures["uncertainty-private-data"] == ["missing_expected_answer_marker"]


def test_benchmark_contains_multilingual_shopping_and_support_grounding_cases():
    selected = {
        case.case_id: case
        for case in AI_EVALUATION_CASES
        if case.category in {"shopping_grounding", "support_grounding"}
    }

    assert set(selected) == {
        "shopping-live-price-english",
        "shopping-live-price-bangla",
        "support-return-policy-banglish",
    }
    assert all("guess" in case.prompt.lower() or "বানিয়ে" in case.prompt
               for case in selected.values())
    support_case = selected["support-return-policy-banglish"]
    assert _check_case(support_case, "The policy says 14 days; contact support if needed.")
    assert not _check_case(
        support_case,
        "Order data is not provided, so I cannot verify; check the order page or support policy.",
    )


def test_benchmark_syntax_check_never_executes_generated_code(tmp_path):
    marker_path = tmp_path / "should-not-exist"
    source = (
        "```python\n"
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).touch()\n"
        "def count_even(numbers):\n"
        "    return 0\n"
        "```"
    )
    code_case = next(
        case for case in AI_EVALUATION_CASES
        if case.case_id == "coding-function-syntax"
    )

    failures = _check_case(code_case, source)

    assert failures == []
    assert not marker_path.exists()


def test_benchmark_reports_provider_failures_without_answer_content():
    report = evaluate_ai(lambda _prompt: {"ok": False, "fallback": "private endpoint unavailable"})

    assert report["failed_count"] == report["case_count"]
    assert all(
        result["checks"] == ["model_unavailable_or_empty_answer"]
        for result in report["results"]
    )
    assert "private endpoint unavailable" not in str(report)


def test_benchmark_cli_fails_closed_without_a_private_local_model(app):
    result = app.test_cli_runner().invoke(args=["benchmark-ai"])

    assert result.exit_code != 0
    assert "Configure the private local AI endpoint and model" in result.output
    assert "benchmark-ai" in app.cli.commands
