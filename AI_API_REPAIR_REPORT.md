# Food-Web AI API Repair Report

## মূল সমস্যা

সর্বশেষ provider refactor-এ direct provider request-কে external fallback gate-এর অধীনে নেওয়া হয়েছে। `AI_EXTERNAL_ENABLED`, positive monthly budget, model pricing, customer consent এবং external-call notice—সবগুলো শর্ত পূরণ না হলে API request পাঠানো হয় না। Uploaded configuration-এ `openrouter/free` মডেলের input/output rate `0`, আর SQLite local development-এ Telegram Security Bot secrets ইচ্ছাকৃতভাবে load হয় না। ফলে local notice delivery check ব্যর্থ হতে পারে এবং OpenRouter request পাঠানোর আগেই আটকে যায়।

## কী পরিবর্তন করা হয়েছে

- `AI_API_IS_FREE` যোগ করা হয়েছে। এটি default-off এবং শুধু explicit opt-in-এর পরে OpenRouter HTTPS host ও `openrouter/free`/`:free` model slug মিলে গেলে zero-price path অনুমোদন করে।
- Budget logic-এ verified $0 call গ্রহণ করা হয়েছে; positive external monthly budget enablement gate হিসেবেই থাকে।
- `AI_EXTERNAL_LOCAL_NOTICE_MODE` যোগ করা হয়েছে। এটি শুধু explicit opt-in, `ENVIRONMENT=development` এবং SQLite database একসাথে সত্য হলে metadata-only external-call notice সংরক্ষণ করে। Local mode Telegram-এ request পাঠায় না। Production-এ Telegram notice delivery gate অপরিবর্তিত।
- Customer AI consent-এ দেখানো ভাষা এক configured external provider-এর সঙ্গে মিলিয়ে আপডেট করা হয়েছে।
- `scripts/enable_openrouter_free_local.py` যোগ করা হয়েছে। এটি local JSON-array `.env` যাচাই করে, backup বানায়, free-model settings enable করে; API key print বা পরিবর্তন করে না।
- নতুন regression tests এবং local setup documentation যোগ হয়েছে।

## চালানোর ধাপ

1. এই ZIP-এ `.env` ইচ্ছাকৃতভাবে রাখা হয়নি। তোমার নিজের private/original project থেকে `.env` ফাইলটি repaired project root-এ কপি করো। `.env` কখনো GitHub-এ commit বা public-এ share করবে না।
2. Local terminal-এ `APP_ENV=development` এবং SQLite database ব্যবহার হচ্ছে নিশ্চিত করো।
3. Project root থেকে চালাও: `python scripts/enable_openrouter_free_local.py`
4. Database table/migration update করো: `flask --app run.py db upgrade`
5. Flask server restart করে Customer AI page-এ গিয়ে **Allow external AI assistance**-এ নিজে সম্মতি দাও। `hello`-এর মতো সাধারণ প্রশ্ন দিয়ে পরীক্ষা করো।

Script production environment বা PostgreSQL database detect করলে পরিবর্তন না করেই থেমে যাবে। Production deployment-এ `AI_EXTERNAL_LOCAL_NOTICE_MODE=false` রাখবে; সেখানে Security Bot token/admin recipients ও provider pricing ঠিকভাবে configure করতে হবে। Free-model availability/usage provider-এর নিজস্ব rate-limit-এর অধীন। Zero-cost request-এর জন্য monthly dollar budget নিজে থেকে request count সীমাবদ্ধ করে না, তাই application/provider rate limits বজায় রাখতে হবে।

## Validation ও সীমাবদ্ধতা

- Modified Python files: `compileall` pass করেছে।
- `.env.example`: JSON syntax ও unique setting names validate হয়েছে।
- Free-model guard: ৮টি isolated input case pass করেছে।
- Regression tests source-এ যোগ করা হয়েছে, কিন্তু এই execution environment-এ Flask dependency install না থাকায় full pytest suite চালানো যায়নি। Actual OpenRouter call-ও real API key-সহ invoke করে যাচাই করা হয়নি.
- Uploaded archive-এর pre-existing `pytest_catalog.log`-এ পুরোনো run-এর চারটি unrelated homepage/catalog/translation test failure ছিল; তা current run হিসেবে বিবেচনা করা হয়নি এবং stale log repaired ZIP থেকে বাদ দেওয়া হয়েছে.

## Security note

Uploaded ZIP-এ `.env` credential config ও cookie artifact ছিল। Repaired ZIP থেকে `.env`, cookie artifact, `.git` history, virtualenv/cache, local datasets এবং stale logs বাদ দেওয়া হয়েছে। যদি original ZIP কোথাও public বা অন্যের কাছে share করা হয়ে থাকে, exposed API/database/mail/Telegram/payment credentials rotate করো এবং সম্ভাব্য live session revoke/logout করো।
