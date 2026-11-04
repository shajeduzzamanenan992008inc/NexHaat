# NexHaat Animation and Motion Standard

**Status:** In progress; updated 2026-11-03  
**Applies to:** React/Vite website and native Android application  
**Product direction:** Hybrid Ultra — purposeful feedback with short, lightweight motion.

## Goals

- Keep NexHaat's existing visual identity, neumorphic surfaces, responsive layouts, and 3D product-card interaction.
- Use motion to explain a state change or acknowledge an action; never make motion a prerequisite for reading or acting.
- Prefer opacity and small transforms. Avoid large particle bursts, heavy blur, long choreography, and always-moving decoration.
- Keep durations aligned across platforms while allowing each platform to use its native animation behavior.

## Shared timing and easing

| Token | Duration | Use |
|---|---:|---|
| Instant | 100 ms | Tooltip and tiny status feedback |
| Fast | 150 ms | Press, selection, and badge feedback |
| Normal | 280 ms | Card, drawer, and component changes |
| Page | 320 ms | Small page-content entrance |
| Major | 450 ms | Dialog or significant state change |

The legacy `complex` token aliases 450 ms for source compatibility. New work must not introduce motion longer than 450 ms without a specific usability reason. Curves are `cubic-bezier(0.175, 0.885, 0.32, 1.275)` for spring-like feedback, `cubic-bezier(0, 0, 0.2, 1)` for entrances, `cubic-bezier(0.4, 0, 1, 1)` for exits, and `cubic-bezier(0.4, 0, 0.2, 1)` for standard state changes.

## Entry, exit, and loading

- Website view changes currently use the app's in-memory view state and a 320 ms entrance. Browser URL/history navigation and coordinated exit transitions are not implemented; do not imply that they are.
- Do not delay first interaction for a decorative intro. The website splash begins auto-dismiss after 300 ms and fades for 150 ms, can be skipped, allows pointer access to the underlying page, and immediately exits when reduced motion is requested. It does not simulate authentication or network progress.
- Loading indicators must reflect real pending work. Skeletons should be static or use a restrained shimmer; never use a fake percentage to imply completed work.
- Keep content, validation errors, and payment/order results available without animation.

## Reduced motion and accessibility

- Website CSS honors `prefers-reduced-motion`, disables smooth scrolling, and reduces animation and transition duration. JavaScript effects such as confetti must independently check the preference.
- Android Compose animations must respect the system animator duration scale. The catalog skeleton also checks Android's animation setting before starting its repeating shimmer.
- Preserve keyboard focus, visible focus styles, screen-reader labels, and live feedback. Decorative animation is hidden from assistive technology.
- Avoid shake, zoom, parallax, and repeated movement for essential status. Reduced-motion mode must not hide or defer information.

## Platform implementation

- Website timing values live in `src/lib/motionTokens.ts` and CSS variables in `src/index.css`. Reuse these tokens instead of adding unrelated hard-coded durations.
- Android equivalents live in `android/app/src/main/java/com/nexhaat/app/ui/theme/MotionTokens.kt`. Compose may use native springs where useful, but should stay within the shared time scale and honor system animation settings.
- The website product-card tilt is pointer-driven and bounded. Do not enable hover-only tilt as the sole interaction on touch devices.
- Celebration confetti is reduced to 80 particles total and is suppressed under `prefers-reduced-motion`.

## Current implementation status

- **Website:** PARTIAL. Shared tokens, page entrance, reduced-motion CSS, reduced confetti, and a short non-blocking splash are implemented. Many existing components still have local Tailwind/CSS durations; view exit transitions and URL/history navigation are not implemented. No browser visual or performance measurement was run for this change.
- **Android:** PARTIAL. Shared tokens now align with the website and product-card press feedback uses them. Android navigation transitions are not configured; existing banner and AI animations have not all been audited for reduced-motion behavior. No device run was available for this change.
- **Cross-platform runtime parity:** NOT TESTED. Source-level timing alignment does not prove equal runtime behavior.

## Website coverage and local preview record — 2026-11-04

The React view registry in `src/App.tsx` contains these 13 views. Each is wrapped
by the shared `animate-view-enter` page entrance; this is an in-memory view
change, not URL/history routing.

| View | Shared page entrance | Specific motion coverage |
|---|---|---|
| Home | Yes | Shared page entrance |
| Catalog | Yes | Product-card 3D tilt and token-based image zoom |
| Deals | Yes | Shared page entrance and product-card motion |
| Product detail | Yes | Shared page entrance and product-card motion in related-product shelves |
| Checkout | Yes | Shared page entrance; existing auth dialog keeps its current flow |
| Order confirmation | Yes | Shared page entrance; existing completion feedback is preserved |
| My orders | Yes | Shared page entrance; existing return dialog keeps its current flow |
| Wishlist | Yes | Shared page entrance and product-card motion |
| Notifications | Yes | Shared page entrance |
| Seller portal | Yes | Shared page entrance; existing seller forms and dialogs are preserved |
| Rider portal | Yes | Shared page entrance |
| Admin portal | Yes | Shared page entrance |
| Support | Yes | Shared page entrance |

Shared interactions now use the same tokens for modal entrance, navigation
popovers, mobile-menu open/close, cart and AI drawer open/close, AI message
arrival, active desktop navigation indicators, and product image zoom. Drawer and
mobile-menu exit animation is skipped immediately when reduced motion is active.
Other existing dialogs animate on entry and still unmount immediately on close;
coordinated dialog exit is a remaining refinement. Existing route selection,
history behavior, commerce logic, API calls, and AI request/stream handling were
not changed.

### Local preview and verification

- Start the existing local web/Express development command with `npm run dev`.
- Open `http://127.0.0.1:3000/`; stop the server with Ctrl+C in its terminal.
- The existing local server returned HTTP 200 for `/` during this pass. The Flask
  service on port 5000 was not started because this motion change does not require
  backend state; API-dependent runtime behavior therefore remains unverified.
- `npm run build`: PASS (TypeScript and Vite build); Vite still reports the
  existing 1,084.84 kB main chunk warning.
- `npm test`: PASS (9 Node security tests).
- `node --import tsx --test src/lib/motionTokens.test.ts`: PASS (5 tests).
- `git diff --check`: PASS; Git emitted existing CRLF-to-LF notices for two
  modified workflow files.
- Live browser screenshot, console/network inspection, desktop/mobile runtime
  checks, and reduced-motion runtime checks: NOT TESTED. Codex local browser
  control is disabled in Work settings; this environment rejected launching
  Chrome, and the attempted REA scenario was rejected during input validation
  before any browser action ran.

Source-level reduced-motion coverage is present in `src/index.css` and the new
presence hook, but it is not a substitute for runtime accessibility verification.

