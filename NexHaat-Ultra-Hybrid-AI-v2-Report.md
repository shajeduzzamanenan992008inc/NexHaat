# NexHaat Ultra Hybrid AI v2 — Change & Verification Report

## এই ধাপে কী যোগ হলো

1. `app/ai/core/specialist_router.py` — deterministic task-aware specialist selector.
   - Shopping/product/budget প্রশ্নে Sol → Luna অগ্রাধিকার
   - Engineering/API/bug/test প্রশ্নে Forge → Luna
   - Audit/security/reliability প্রশ্নে Luna → Forge
   - Planning/roadmap/design প্রশ্নে Astra → Luna
   - সাধারণ প্রশ্নে general priority
2. `app/ai/core/provider.py`-এর existing multi-specialist fusion path এখন প্রথম দুই provider-কে অন্ধভাবে নেওয়ার বদলে task-fit অনুযায়ী pair বেছে নেয়।
3. নতুন `tests/test_ai_specialist_router.py` যোগ হয়েছে।
4. বাংলা operations guide ও change report update হয়েছে।
5. ZIP থেকে `.venv`, cache, `.pyc`, local SQLite database এবং active `.env` বাদ রাখা হয়েছে। `.env.example` রাখা হয়েছে।

## Verification

- `py_compile` — PASS.
- `compileall` across `app`, `scripts`, `tests` — PASS.
- `.env.example` JSON validation — PASS; 105 setting names, no duplicates.
- Router direct-import focused checks — **8 assertions PASS** covering shopping/engineering/review/planning/general classification plus pair selection.
- `pytest` — **NOT RUN**: import of project test fixtures fails because Flask is not installed in this execution environment. `pip install -r requirements.txt` also failed because the package index could not resolve via network DNS. This is an environment limitation, not a passing test result.
- Live model inference, Telegram delivery, marketplace end-to-end actions, PostgreSQL, payment/webhook, and production deployment — NOT VERIFIED.

## Configuration status remains a blocker

The uploaded project had no active `.env`; `.env.example` is only a template. Local AI URL/model are not configured, direct API is disabled/incomplete, external fallback is disabled and no live provider credentials were supplied. Therefore, no live AI answer or API integration is claimed as tested.

## Important boundaries

Astra/Luna/Sol/Forge are prompt personas, not separately trained GPT-6 models. The router only chooses among the provider/model configurations already supplied to `AI_SPECIALISTS`. It adds no external call by itself and does not bypass consent, provider notice, budget, scope, or security gates. Routing is keyword-based and may choose the wrong category on ambiguous prompts.
