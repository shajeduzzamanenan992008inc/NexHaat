"""Offline-safe, non-persisting quality checks for the configured local AI."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class AIEvaluationCase:
    case_id: str
    category: str
    prompt: str
    required_groups: tuple[tuple[str, ...], ...] = ()
    required_function: str | None = None


AI_EVALUATION_CASES = (
    AIEvaluationCase(
        "math-multiplication",
        "math",
        "Calculate 17 × 19. Reply with the final value on a line beginning FINAL:.",
        (("323",),),
    ),
    AIEvaluationCase(
        "math-discount",
        "math",
        "বাংলায় হিসাবটি করো: ১২০০ টাকা থেকে ১৫% ছাড় দিলে ছাড় কত টাকা এবং শেষ দাম কত? "
        "উত্তরটি FINAL: ছাড়=..., দাম=... আকারে দাও।",
        (("180",), ("1020",)),
    ),
    AIEvaluationCase(
        "math-percentage-trap",
        "reasoning",
        "A price is 1000 taka. It rises by 20%, then the new price is discounted by 20%. "
        "Give the final price and net percentage change from the original, on a FINAL: line.",
        (("960",), ("4%", "4 percent", "4 per cent")),
    ),
    AIEvaluationCase(
        "bangla-understanding",
        "multilingual",
        "তিনটি সংখ্যার গড় ১২। প্রথম দুটি সংখ্যা ৯ ও ১৫ হলে তৃতীয় সংখ্যাটি কত? "
        "শুধু উত্তর নয়, এক লাইনে হিসাবও দেখাও।",
        (("12",),),
    ),
    AIEvaluationCase(
        "banglish-understanding",
        "multilingual",
        "Duita notebook er dam 35 taka kore, ar ekta pen 20 taka. Shob mile koto? "
        "Ek line e hisab shoho answer dao.",
        (("90",),),
    ),
    AIEvaluationCase(
        "coding-function-syntax",
        "coding",
        "Write a Python function named count_even(numbers) that returns how many values "
        "in the input list are even. Return only a Python code block.",
        required_function="count_even",
    ),
    AIEvaluationCase(
        "coding-debugging",
        "coding",
        "Explain the bug in this Python function and describe a safe fix: "
        "def add_item(item, items=[]): items.append(item); return items. "
        "Your explanation must name the cause and the safe default-value pattern.",
        (("mutable default",), ("none",)),
    ),
    AIEvaluationCase(
        "uncertainty-private-data",
        "grounding",
        "Tell me the current delivery status and stock for private order NH-EVAL-000000. "
        "Do not guess; say whether you can verify these account-specific facts.",
        (("cannot verify", "can't verify", "do not have access", "don't have access",
          "যাচাই করতে পারি না", "তথ্য যাচাই করা সম্ভব নয়"),),
    ),
    AIEvaluationCase(
        "shopping-live-price-english",
        "shopping_grounding",
        "What is the exact current price and stock of the Mango Blender? No live catalog "
        "result is supplied. Do not guess; explain how to verify it.",
        (("live catalog", "current catalog", "live data", "cannot verify",
          "can't verify", "যাচাই করতে পারি না"),),
    ),
    AIEvaluationCase(
        "shopping-live-price-bangla",
        "shopping_grounding",
        "এই পণ্যের বর্তমান দাম ও stock এখন কত? কোনো live catalog result দেওয়া হয়নি। "
        "দাম বানিয়ে না বলে কীভাবে যাচাই করতে হবে বলো।",
        (("লাইভ ক্যাটালগ", "বর্তমান ক্যাটালগ", "লাইভ ডেটা", "যাচাই করতে পারি না",
          "যাচাই করা সম্ভব নয়", "cannot verify"),),
    ),
    AIEvaluationCase(
        "support-return-policy-banglish",
        "support_grounding",
        "Amar order-er return window exactly kotodin? Ekhane kono order ba verified policy "
        "data deya hoyni. Guess na kore bolo order page/support diye verify korte hobe.",
        (
            ("cannot verify", "can't verify", "no order data", "not provided",
             "যাচাই করতে পারি না", "নিশ্চিত করে বলা যায় না"),
            ("order page", "support", "policy", "নীতিমালা", "সহায়তা"),
        ),
    ),
)


_BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_CODE_BLOCK = re.compile(r"```(?:python|py)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).translate(_BANGLA_DIGITS).casefold()


def _check_case(case: AIEvaluationCase, answer: str) -> list[str]:
    normalized = _normalized(answer)
    failures = []
    for alternatives in case.required_groups:
        if not any(
            re.search(r"(?<!\w)" + re.escape(_normalized(term)) + r"(?!\w)", normalized)
            for term in alternatives
        ):
            failures.append("missing_expected_answer_marker")

    if case.required_function:
        code_match = _CODE_BLOCK.search(answer)
        candidate = code_match.group(1) if code_match else answer
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            failures.append("invalid_python_syntax")
        else:
            if not any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == case.required_function
                for node in ast.walk(tree)
            ):
                failures.append("missing_expected_function")
    return failures


def evaluate_ai(respond):
    """Run fixed prompts and return marker-only results without retaining answers."""
    results = []
    for case in AI_EVALUATION_CASES:
        try:
            response = respond(case.prompt)
            answer = response.get("answer") if isinstance(response, dict) else None
            failures = _check_case(case, answer) if isinstance(answer, str) else [
                "model_unavailable_or_empty_answer"
            ]
        except Exception as error:
            failures = [f"request_failed_{type(error).__name__}"]
        results.append({
            "case_id": case.case_id,
            "category": case.category,
            "passed": not failures,
            "checks": failures or ["automated_markers_passed"],
        })
    return {
        "case_count": len(results),
        "passed_count": sum(item["passed"] for item in results),
        "failed_count": sum(not item["passed"] for item in results),
        "human_review_required": True,
        "results": results,
    }
