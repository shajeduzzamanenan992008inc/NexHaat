# Stage 14 — Multimodal AI Builder ও Project Guardian

## সারাংশ

NexHaat Admin-এর AI image, voice, file, folder ও code project বিশ্লেষণ করবে। Local model আগে চেষ্টা করবে; কঠিন task-এ Admin API assistance চালু রাখলে configured external provider ব্যবহার করবে। প্রতিটি external AI provider call-এর জন্য Security Bot-এ আলাদা Telegram notice যাবে। Main deployment ও nightly scan-এ bug পেলে AI sandbox-এ fix candidate বানাবে, test চালাবে এবং Admin-কে জানাবে।

সব সমস্যার নিখুঁত সমাধানের নিশ্চয়তা দেওয়া যাবে না; completion tests ও review evidence দিয়ে যাচাই হবে।

## Implementation

- **Local AI ও provider routing:** Stage 13-এর shared Core/private GPU endpoint ব্যবহার হবে; quantized `Qwen3.5-9B` local candidate। এর vision ও coding ক্ষমতা model card-এ নথিভুক্ত; নির্বাচিত GPU-তে serving ও quality আগে যাচাই হবে। [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) OpenAI, Anthropic, Gemini, DeepSeek এবং OpenAI-compatible endpoint সমর্থিত হবে। Local-first routing-এর পর জটিল task-এ Admin consent, enabled API setting ও positive monthly cap থাকলে provider নির্বাচন হবে; প্রতি task-এ সর্বোচ্চ তিনটি external call।
- **প্রতি API call-এ Telegram notice:** প্রতিটি outbound external AI request—specialist, verifier বা retry—এর আগে unique call event durable outbox-এ লেখা হবে এবং allowlisted Admin IDs-এ Security Bot notice পাঠানো হবে। Notice-এ provider/model, call purpose, job ID, সময়, আনুমানিক reserved cost ও “started” status থাকবে; prompt, code, media, secret বা ব্যক্তিগত তথ্য থাকবে না। Telegram সাময়িকভাবে unavailable হলে notice retry queue-তে থাকবে। Recipient, bot token বা durable event storage না থাকলে external call হবে না; local AI চলতে পারবে। Local private-model call-কে external API notice হিসেবে ধরা হবে না।
- **Multimodal Admin workspace:** Image; voice input/reply; browser-এ live voice conversation; `.txt`, `.md`, source code, PDF, DOCX, XLSX/CSV; এবং ZIP folder/project analysis থাকবে। Telegram-এ voice note ও voice reply থাকবে। Upload type ও size যাচাই হবে; ZIP path traversal, symlink ও decompression abuse প্রত্যাখ্যান হবে। External provider-এ raw media পাঠাতে প্রতিটি upload/session-এর অনুমতি লাগবে।
- **Project analysis ও bug fix:** Admin নতুন Flask/Python বা static HTML/CSS/JavaScript project বানাতে, NexHaat repository বিশ্লেষণ করতে এবং নির্বাচিত/upload করা project পরীক্ষা করতে পারবে। NexHaat main deployment-এর সময় ও nightly scan হবে; manual scan-ও থাকবে। Bug পেলে AI isolated sandbox-এ patch এবং regression test তৈরি করবে। Confirmed high-risk security bug বা reproducible critical test failure deployment আটকে দেবে; scanner outage warning দেবে, deployment আটকে দেবে না। Patch merge/deploy-এর আগে Admin approval লাগবে।
- **Telegram scan alert:** Existing Security Bot allowlist ও durable retry flow ব্যবহার হবে। প্রতিটি confirmed finding-এর notice-এ severity, commit/job reference, test status এবং authenticated Admin review link থাকবে; raw code বা secret থাকবে না। একই finding পুনরায় এলে deduplicate হবে।
- **ভবিষ্যতের শেখা:** Test-pass করা API-assisted fix-এর sanitized lesson, source/version ও test evidence Admin approval-এর পর private RAG memory-তে যাবে। পরের অনুরূপ সমস্যায় AI সেটি retrieve করবে। Raw provider transcript জমা হবে না এবং model weights স্বয়ংক্রিয়ভাবে train হবে না।
- **Privacy ও storage:** Code পাঠানোর অনুমতি project-ভিত্তিক; media পাঠানোর অনুমতি upload/session-ভিত্তিক। Project save opt-in হবে। Sandbox non-root ও disposable থাকবে; host secrets, production database, Docker socket এবং arbitrary internet access থাকবে না। Additive migration-এ job/project, approved lessons এবং per-call Telegram outbox metadata রাখা হবে।

## Interface ও যাচাই

- Admin job API: `POST /admin/ai-builder/jobs`, `GET /admin/ai-builder/jobs/{id}`, diff/export/delete actions। Deployment scan-এর জন্য signed internal scan-queue interface থাকবে; browser বা Telegram সরাসরি worker চালাতে পারবে না।
- Tests-এ local-only fallback, provider selection/timeout, budget cap, code/media consent, **প্রতি external request-এ একটিমাত্র deduplicated Telegram event**, delivery retry, missing-bot fail-closed, prompt/code/media redaction, RAG approval, file/ZIP validation, sandbox escape ও secret-access denial যাচাই হবে।
- Project generation, NexHaat patch, main/nightly/manual scans, high-risk deployment gate, scanner outage warning, Telegram allowlist এবং voice/image/file analysis integration tests pass করতে হবে। Curated coding tasks-এর অন্তত 70% hidden tests pass, full suite ও migration checks pass এবং private GPU/API/Telegram staging smoke test সম্পন্ন না হওয়া পর্যন্ত Stage 14 Complete হবে না।

## Assumptions

- “প্রতিটি API call” বলতে প্রতিটি **external AI model-provider request** বোঝানো হয়েছে; Telegram notice নিজেই Telegram service call, আর private local-model request আলাদা থাকবে।
- Provider catalog-এর scope হলো চারটি named provider ও OpenAI-compatible service; ভিন্ন protocol হলে নতুন adapter লাগবে।
- Unsaved media ২৪ ঘণ্টার মধ্যে মুছবে; saved project ও approved lesson Admin মুছতে পারবে।
- External API monthly budget-এর অঙ্ক এখনো নির্দিষ্ট নয়; cap না থাকলে external calls বন্ধ থাকবে। কোনো paid GPU/API service এই plan থেকে provision হবে না।
- Stage 13 In Progress থাকবে; Stage 10 ও 11-এর status অপরিবর্তিত থাকবে।
