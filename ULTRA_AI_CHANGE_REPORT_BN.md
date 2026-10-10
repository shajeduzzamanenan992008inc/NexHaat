# NexHaat Ultra Hybrid AI — Change Report

## এই ZIP-এ কী পরিবর্তন হয়েছে

1. Existing specialist-provider flow-তে optional persona instructions যোগ হয়েছে: **Astra** (planning), **Luna** (independent review), **Sol** (shopping/value), **Forge** (engineering). Persona নামগুলো `.env.example`-এ configure করা যায় এবং `AI_SPECIALISTS`-এর actual model/provider-এ চলে।
2. `scripts/diagnose_ai.py` যোগ হয়েছে। এটি active `.env`/process settings থেকে configuration readiness দেখায়, key/URL/response body print করে না, এবং default-এ network request পাঠায় না।
3. `--probe-local` ও `--probe-direct` explicit flag যোগ করা হয়েছে। এগুলোর যেকোনো একটি চালালে একটি ছোট inference request পাঠানো হয়; provider charge করতে পারে।
4. Task-aware specialist router (`app/ai/core/specialist_router.py`) ও regression tests যোগ করা হয়েছে: shopping → Sol/Luna, engineering → Forge/Luna, review/security → Luna/Forge, planning → Astra/Luna। এটি বিদ্যমান consent/budget/notice gates এড়িয়ে যায় না।
5. Bangla operations guide, README link, regression tests ও master-plan handoff update করা হয়েছে।

## Verification

- AI Core + Stage 13 + persona: **84 passed**.
- AI features + API + Telegram + free-model + evaluation: **100 passed**.
- Config + persona: **17 passed**.
- Diagnostics + persona + config: **20 passed**.
- মোট **201টি distinct test case** উপরের focused groups-এ pass করেছে।
- `py_compile`, `compileall`, `.env.example` JSON validation এবং duplicate setting-name check pass করেছে।
- একটি combined focused-test rerun execution limit-এ timeout করেছে; তবে প্রত্যেক listed group আলাদাভাবে successful exit করেছে। এটি full-suite pass দাবি নয়।
- Full project test suite চালানো হয়নি। Live provider inference, live Telegram delivery, Docker sandbox, GPU, PostgreSQL/pgvector, payment callback ও production deployment যাচাই করা হয়নি।

## Uploaded ZIP থেকে পাওয়া live configuration blocker

এই ZIP-এ সক্রিয় `.env` নেই; `.env.example` শুধু template। Diagnostic ফলাফল:

- Local AI: URL ও model অনুপস্থিত।
- Direct API: disabled; key/model/URL সক্রিয়ভাবে configured নয়।
- External fallback: disabled, budget/provider incomplete।
- External-call notice path: configured নয়।

তাই বর্তমান ZIP-এর code-এ AI architecture থাকলেও এই workspace-এ **live model call সফল হয়েছে বলা যাবে না**। Provider-এর valid endpoint/model/key এবং consent/budget/notice settings private runtime environment-এ বসানোর পর `python scripts/diagnose_ai.py` দিয়ে যাচাই করতে হবে।

## মনে রাখতে হবে

Astra/Luna/Sol/Forge এখানে agent persona; এগুলো নিজস্ব trained GPT-6 model বা API নয়। Actual reasoning/quality নির্ভর করবে যে বাস্তব provider/model configure করা হবে তার উপর। Amazon-এর মতো shopping capabilities-এ NexHaat-এর catalog, order, inventory, payment ও delivery integrations-ই authoritative থাকবে।


## Second-pass (task-aware routing) verification

- `py_compile` এবং পুরো `app`, `scripts`, `tests` tree-তে `compileall` সফল।
- `.env.example` JSON validation সফল।
- নতুন router-কে dependency-free direct import করে **8টি focused assertions** pass করেছে (task classification ও shopping/engineering/review selection)।
- Full pytest rerun attempted but could not start because this execution environment does not have Flask installed; pip installation also failed because package index/network DNS is unavailable. Therefore, **the new pytest module has not been run under pytest here**, and the earlier 201 focused passes refer to the previous build only.


## Public-hosting hardening pass (2026-10-10)

- `.env.example` এখন standard dotenv format; 105টি unique settings আছে এবং sensitive fields demo/blank রাখা হয়েছে। Azure Advanced Edit-এর জন্য আলাদা `.azure-app-settings.example.json` যোগ করা হয়েছে।
- CI workflow Python 3.12 ব্যবহার করে, source compile ও environment template যাচাই করে, full pytest suite চালিয়ে, তারপরই Azure production deploy করে।
- Production dependency থেকে `pytest` সরিয়ে `requirements-dev.txt`-এ রাখা হয়েছে; অপ্রয়োজনীয় `psycopg2-binary` dependency বাদ দেওয়া হয়েছে, কারণ project-এর SQLAlchemy URL `psycopg` v3 ব্যবহার করে।
- `scripts/check_env_example.py`, read-only `scripts/smoke_test.py`, deployment regression tests এবং `docs/operations/public-launch.md` যোগ করা হয়েছে।
- Verified locally here: 105 dotenv keys and 100 statically referenced env keys covered; Azure JSON has 105 unique settings; new Python files compile; workflow YAML parses. Full pytest and live deployment could not be run here because Flask is missing and package-index network access failed.
- Public launch still requires the actual hosting account, PostgreSQL, HTTPS domain, mail, storage/ClamAV, admin provisioning, backups, and any live payment/AI/Telegram credentials to be configured and smoke-tested.
