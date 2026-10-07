# Stage 14 — NexHaat Shopping AI

## Summary

NexHaat-এ Amazon-এর shopping assistant-এর মতো customer AI তৈরি করব। বর্তমান shared AI Core, catalog search, recommendations, comparison, voice/image search এবং confirmed cart suggestions পুনরায় ব্যবহার করে customer shopping experience উন্নত করব। NexHaat-এর নিজস্ব design বজায় থাকবে; Amazon-এর interface নকল হবে না।

## Changes

- **কথোপকথনে পণ্য খোঁজা:** বাংলা, Banglish ও English-এ shopping request বুঝে catalog-এর পণ্য, বর্তমান দাম, stock, options ও product links দেখাবে। বাস্তব product data ও approved reviews থেকে প্রশ্নের উত্তর, ২–৩টি পণ্যের তুলনা এবং “কোনটি আমার জন্য ভালো?” ধরনের সিদ্ধান্ত-সহায়তা দেবে।
- **ছবি, voice ও personalization:** ছবি থেকে মিল আছে এমন পণ্য খোঁজা এবং voice-এ প্রশ্ন করার সুবিধা দেবে। Customer সম্মতি দিলে recent views, wishlist ও shopping history থেকে সুপারিশ করবে। ছবি, voice বা chat স্থায়ীভাবে সংরক্ষণ করবে না।
- **দাম ও customer support:** দেখা দামের ইতিহাস এবং target-price alert যোগ করবে। Alert customer-এর বিদ্যমান in-app notification-এ যাবে; পুরোনো দামের তথ্য না থাকলে AI ইতিহাস বানিয়ে দেখাবে না। নিজের order, delivery, return ও refund-এর প্রশ্নে বিদ্যমান account-scoped services ব্যবহার করবে।
- **Cart ও নিরাপত্তা:** AI পণ্য/পরিমাণ প্রস্তাব করবে; customer নিশ্চিত করলে বর্তমান price ও stock যাচাই করে cart বদলাবে। Checkout বা payment AI করবে না। অন্য customer-এর cart, order বা ব্যক্তিগত তথ্য প্রকাশ করবে না।
- **Provider ও Telegram notice:** Local-first Core আগে উত্তর দেবে। User consent এবং নির্ধারিত spending limit থাকলে কঠিন প্রশ্নে configured external model ব্যবহার করা যাবে। প্রতিটি external model request-এর আগে metadata-only Telegram notice পাঠানোর ব্যবস্থা থাকবে; notice গ্রহণ না হলে ওই external request পাঠানো হবে না। Prompt, code, image, credentials বা ব্যক্তিগত তথ্য notice-এ থাকবে না।
- **Stage tracking:** বর্তমান Stage 13-এর status In progress থাকবে; তার private GPU ও staging gate-গুলো আলাদা থাকবে। Coding/project analysis ও automatic project guardian এই shopping-focused ধাপের বাইরে থাকবে, পরে আলাদা করে পরিকল্পনা হবে।

## Verification

- Catalog-grounded product search, detail Q&A, comparison, recommendation এবং ভুল/অনুপস্থিত তথ্য হলে uncertainty জানানোর পরীক্ষা।
- Bangla/Banglish/English এবং image/voice input যাচাই; media সংরক্ষিত হচ্ছে না তা নিশ্চিত করা।
- Customer ownership, অনুমতিবিহীন personalization, ভুল/পুরোনো price, stock পরিবর্তন, price alert ও notification opt-in পরীক্ষা।
- Cart পরিবর্তনের আগে confirmation এবং server-side price/stock revalidation যাচাই।
- প্রতিটি external request-এর Telegram notice, notice ব্যর্থ হলে provider call বন্ধ থাকা, consent/spend limit এবং provider timeout পরীক্ষা।
- Additive migration-এর upgrade/downgrade ও বর্তমান AI, catalog, cart এবং order test suite চালানো। Live private GPU ও deployed Telegram acceptance সম্ভব না হলে সেগুলোকে operator gate হিসেবেই নথিবদ্ধ করা হবে।

## Assumptions

- “Amazon-এর মতো” বলতে customer shopping assistant বোঝানো হয়েছে—Amazon-এর branding বা visual copy নয়।
- Price history ও alerts customer-এর জন্য opt-in হবে; alert delivery বিদ্যমান in-app notification দিয়ে শুরু হবে।
- কোনো API credential বা hosting secret repository-তে যোগ হবে না।
