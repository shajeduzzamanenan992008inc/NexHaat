# Google AI Studio Integration Standard

Google AI Studio is NexHaat's primary source for future frontend concepts,
visual direction, animations, and interaction prototypes. Generated code is
reference material until it has been inspected, mapped, tested, and accepted
inside the existing repository. It must not silently replace the Flask
authority, Copilot OTP flow, Express AI capability, Firebase compatibility, or
Android API contract.

## Before copying generated code

1. Record the feature in
   `docs/templates/AI_FEATURE_SUBMISSION_TEMPLATE.md` and assign a unique ID.
2. Inspect `git status --short --branch` and preserve existing changes.
3. Keep the export outside the production tree or in an isolated review branch
   until its files, imports, dependencies, assets, routes, and runtime are
   understood.
4. Inventory React/TypeScript/Vite/CSS, state libraries, routing, Firebase
   Auth/Firestore, mock data, direct `fetch` calls, provider calls, environment
   variables, and generated secrets. Never copy `.env`, service-account files,
   API keys, tokens, or customer data.
5. Search NexHaat for equivalent components, pages, types, API clients,
   services, routes, models, and tests before adding anything.
6. Write the intended file-change plan, affected-feature list, deletion/
   rename/move list, API/data mapping, and rollback before implementation.

## Mapping rules

| Generated concern | NexHaat destination/boundary |
|---|---|
| Page/view | Existing `src/pages` and `src/App.tsx` navigation; preserve lazy loading |
| Reusable UI | Existing `src/components`; extend rather than duplicate |
| Feature state | Existing `src/context/AppContext.tsx` or a reviewed feature-local hook |
| Frontend types | `src/types/index.ts` or an explicitly owned type module |
| Flask session/OTP/CSRF | `src/lib/flaskAuth.ts`; existing Flask OTP templates/routes remain canonical |
| Marketplace API | `src/lib/marketplaceApi.ts` and Flask `/api/v1`; do not call the database from the browser |
| Flask business logic | Existing `app/services`, `app/repositories`, `app/models`, and `app/api` patterns |
| Express/Gemini/science | Existing `server.ts` routes and server-side provider boundary |
| Firebase | Existing `src/lib/firebase.ts` and rules; retain as a separate capability until account linking is approved |
| Android | Existing Retrofit/DTO/interceptor/package paths under `android/app` |
| Tests | Existing Python `tests/`, `src/**/*.test.ts`, or `android/app/src/test/` owner |

Generated marketplace operations must map to Flask server contracts. Client
state, Firebase claims, model output, and mock values never authorize access or
define price, stock, seller, payment, or order status.

## Preserve the design without duplicating the system

Keep the generated design, animations, responsive behavior, accessibility, and
useful feature logic when it fits NexHaat. Adapt imports, state boundaries,
types, and API calls instead of flattening the design into a generic page.
Reuse existing `ProductCard`, drawers, modals, layout tokens, reduced-motion
rules, and shared context where they already provide the same behavior.
Create a new component only when search proves there is no suitable owner.

Do not replace an existing page or route merely because the AI Studio export
contains a similar screen. Use an additive feature flag, adapter, or
compatibility wrapper and obtain explicit approval before canonical-route
selection.

## Firebase, Express, and OTP safeguards

- Firebase Auth/Firestore may remain useful for the preserved AI Studio
  capability, but it does not establish a Flask marketplace session or role.
  Do not auto-link or merge accounts.
- Express Gemini/science endpoints remain auxiliary AI capabilities. Keep keys
  server-side, validate request size/content, bound provider calls, and treat
  output as untrusted.
- Flask remains the only marketplace authority for identity, session, CSRF,
  roles, catalog, price, inventory, checkout, orders, payments, and database.
- Reuse the existing server-rendered Copilot OTP flow. Do not create a second
  OTP provider, verification algorithm, code store, or browser secret path.

## Review and validation gate

Before acceptance, reviewers must inspect:

- broken imports and Vite/TypeScript resolution;
- duplicate routes, API clients, types, components, or service logic;
- direct backend/database/provider access from browser code;
- secrets, unsafe HTML, unvalidated input, IDOR, CSRF/CORS, upload and
  prompt-injection risks;
- mock data fallback and live Flask behavior;
- responsive, keyboard, focus, reduced-motion, loading, error, and empty states.

Run `python scripts\validate_repository_structure.py` after implementation.
Unexpected tracked source deletions, large replacements, or renames are
`REVIEW_REQUIRED`; the checker does not automatically block Google AI Studio
or restore files unless the repository CI invokes `--fail-on-review` and that
workflow has been tested. Compare the final diff with the planned change list.

Run the smallest focused checks plus:

```powershell
python scripts\validate_repository_structure.py
npm run lint
npm run build
python -m pytest -q
.\android\gradlew.bat -p android :app:test --no-daemon
git diff --check
```

Record actual output and label staging, provider, payment, OTP delivery,
device, and restore checks as `NOT TESTED` or `BLOCKED` when unavailable.
