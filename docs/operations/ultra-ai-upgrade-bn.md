# NexHaat Ultra Hybrid AI — বাস্তবায়ন ও চালুর গাইড

## কী যোগ হয়েছে

- **Astra**: লক্ষ্য, সীমাবদ্ধতা, পরিকল্পনা ও উত্তর গুছিয়ে দেওয়ার specialist persona।
- **Luna**: ambiguity, unsupported claim, security/privacy risk ও edge case যাচাই করার independent-review persona।
- **Sol**: shopping/user-value specialist persona; পণ্য নিয়ে প্রশ্নে budget, fit ও trade-off-এ জোর দেয়, কিন্তু database থেকে আসা live price/stock ছাড়া সেগুলো বানিয়ে বলে না।
- **Forge**: engineering/code implementation persona; maintainability, tests, security ও reversible changes-এ জোর দেয়।
- **Task-aware routing**: `specialist_router.py` প্রশ্নের ধরন দেখে configured provider-দের মধ্যে উপযুক্ত pair বেছে নেয়; shopping-এ Sol/Luna, engineering-এ Forge/Luna, review/security-তে Luna/Forge, planning-এ Astra/Luna অগ্রাধিকার পায়।
- Configurable persona label/provider mapping: প্রতিটি persona আসলে `AI_SPECIALISTS`-এ দেওয়া provider/model ব্যবহার করে। নাম বদলানো যায় `AI_OPENAI_AGENT_NAME`, `AI_ANTHROPIC_AGENT_NAME`, `AI_GEMINI_AGENT_NAME`, `AI_DEEPSEEK_AGENT_NAME` দিয়ে।
- `scripts/diagnose_ai.py`: secret না দেখিয়ে configuration readiness ও সাধারণ blockers জানায়। Default mode-এ network call করে না।

## Specialist routing কীভাবে কাজ করে

`app/ai/core/specialist_router.py` একটি deterministic keyword-based router। এটি API-তে নতুন call যোগ করে না; বিদ্যমান multi-specialist path চালু হলে কোন configured pair ব্যবহার হবে তা বেছে নেয়। Task classification ভুল হতে পারে, তাই এই routing-কে quality guarantee হিসেবে ধরা যাবে না। Empty বা সাধারণ prompt হলে general priority ব্যবহার হয়।

## একটি গুরুত্বপূর্ণ সীমা

**Astra, Luna, Sol ও Forge হলো prompt/persona, আলাদা foundation model নয়।** এগুলোকে “GPT-6 Astra/Luna/Sol API” ধরে নেওয়া যাবে না। বাস্তবে কাজ করার জন্য provider-এর বৈধ model ID, base URL ও secret key configure করতে হবে। তিনটি persona চালাতে কমপক্ষে তিনটি valid provider/model configuration দরকার; একই provider-এর alias তৈরি করলেই তিনটি স্বাধীন model পাওয়া যায় না।

NexHaat-এর Shopping AI নিজস্ব database এবং tools দিয়ে product search, budget-based recommendations, comparison, approved-review analysis, image/voice entry points, price alerts, wishlist/cart proposal, order/support assistance প্রদান করে—কিন্তু feature বাস্তবে চালু থাকার জন্য সংশ্লিষ্ট database rows, configured model/media services, migrations ও operator settings ঠিক থাকতে হবে। Amazon-ধরনের customer experience বানানো যায়; Amazon-এর private models, data, logistics বা infrastructure পাওয়া যায় না। NexHaat-এর existing visual identity/3D style বজায় রাখতে হবে; Amazon-এর brand/interface সরাসরি নকল করা হবে না।

## AI কেন API call নাও করতে পারে

1. `.env.example` শুধু template; Flask স্বয়ংক্রিয়ভাবে সেটি load করে না। Local development-এ project root-এ private `.env` বা process environment configure করতে হয়। Hosting-এ provider settings private application settings-এ দিতে হয়।
2. Local-first path-এর জন্য `AI_LOCAL_ENABLED=true`, `AI_LOCAL_BASE_URL` এবং `AI_LOCAL_MODEL` দরকার। URL অবশ্যই সেই চলমান OpenAI-compatible service-এর URL হতে হবে।
3. Paid/direct fallback-এর জন্য valid provider key/model/base URL, `AI_ENABLED=true` এবং request path-এ external consent, `AI_EXTERNAL_ENABLED=true`, positive monthly budget, exact current rates এবং required Security Bot notice path লাগে। Free OpenRouter path কেবল প্রকৃত `openrouter/free` বা `:free` model slug এবং explicit `AI_API_IS_FREE=true`-এর জন্য; provider-side rate limit তবুও প্রযোজ্য।
4. Customer catalog/order/cart তথ্যের জন্য বাহ্যিক সাধারণ LLM fallback ব্যবহার করা হয় না; ওগুলো NexHaat-এর scoped tools/database থেকে আসতে হয়। Security scope external specialist-এ পাঠানো হয় না।

## Configuration diagnosis

Project root থেকে:

```powershell
python scripts/diagnose_ai.py
```

এটি কোনো API request পাঠায় না এবং key/URL value print করে না। একটি test request পাঠাতে চাইলে—শুধু সচেতনভাবে, provider-এর সম্ভাব্য cost মেনে—একটি বেছে নাও:

```powershell
python scripts/diagnose_ai.py --probe-local
python scripts/diagnose_ai.py --probe-direct
```

Probe শুধু response status/shape জানায়; model-এর quality বা production deployment পরীক্ষা করে না। Output-এ secrets বা provider response body দেখানো হয় না।

## Acceptance checklist — “ultra powerful” বলার আগে

- [ ] `.env.example`-এর সব placeholder বদলে private runtime configuration দেওয়া হয়েছে; secrets Git-এ নেই।
- [ ] `python scripts/diagnose_ai.py` expected provider readiness দেখায়।
- [ ] Configured Local model-এর live inference, timeout ও malformed response fallback আলাদাভাবে যাচাই করা হয়েছে।
- [ ] প্রত্যেক external request-এর আগে required metadata-only Security Bot notice সফল হয়; consent/budget/rate-limit gates পরীক্ষা করা হয়।
- [ ] অন্তত দুইটি provider দিয়ে specialist fusion এবং disagreement হলে verifier path পরীক্ষা করা হয়; তিনটি persona label-সহ অন্তত তিনটি real provider হলে third-agent verification চালানো যায়।
- [ ] Catalog/price/stock/order/tool actions বাস্তব database facts ব্যবহার করে এবং sensitive mutation-এ confirmation/permission enforce করে।
- [ ] Existing tests, fresh SQLite migration tests, full regression suite এবং production staging acceptance pass করে।
- [ ] Docker sandbox, private GPU, PostgreSQL/pgvector, live Telegram, payments/webhooks ও deployment gates-এ operator evidence নথিবদ্ধ করা হয়।

No key, prompt, source code, customer details, or model response should be sent through diagnostic or Telegram logs.
