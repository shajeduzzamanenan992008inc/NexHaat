# NexHaat shared design system

## Foundations

| Role | Light | Dark |
|---|---|---|
| Page | `#F3F4F6` | `#07182B` |
| Surface | `#FFFFFF` | `#0B1F3A` |
| Raised surface | `#F8FAFF` | `#102947` |
| Main text | `#0B1F3A` | `#F3F6FC` |
| Muted text | `#53657C` | `#B5C4D8` |
| Border | `#DBE3ED` | `#2C405A` |
| Primary action | `#1769FF` | `#1769FF` |
| Primary link/focus companion | `#0B1F3A` | `#4D91FF` |
| Success | `#238253` | Existing success semantic |
| Destructive/error | `#E1251B` | Error tint `#FF756E` |

## Accessibility decisions

White on `#1769FF` is approximately 4.67:1, meeting WCAG AA for normal text. Deep Navy on `#4D91FF` is approximately 5.36:1. Orange fills use Deep Navy text; small orange text on white is avoided. Focus indicators use a visible blue outline with offset. Success, error and warning also retain textual/icon meaning and are not color-only states.

## Type, spacing and motion

Keep the repository's existing Inter/system sans stack for marketplace pages, Poppins accents where already established, and existing spacing/radius scales. Continue using reusable Tailwind tokens, CSS custom properties, Material 3 roles and existing lucide/Compose icons. Preserve the existing motion tokens and reduced-motion behavior; use small transitions on color, shadow and elevation rather than adding continuous movement to commerce controls.

## Theme implementation

- React uses `AppContext` persistence and the `html.dark` class. Tailwind now uses class-based dark mode so existing dark variants respond to the toggle.
- Flask sets `data-theme` through the shared accessible header control and stores the preference locally; the page follows system theme when no preference is saved.
- Android maps light and dark palettes through `MaterialTheme`; the theme follows the existing system-dark setting.

## Runtime boundaries

`src/index.css` and `tailwind.config.js` define the React palette. `app/static/css/site.css`, `marketplace.css`, `auth.css`, `otp-verification.css` and `ai.css` theme the Flask surfaces. Android role colors live in `ui/theme/Color.kt` and `Theme.kt`. CSS colors must never imply that a preview action has reached Flask or that a payment succeeded.
