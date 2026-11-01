---
applyTo: "**/*.{js,jsx,ts,tsx,css,scss}"
---

# NexHaat frontend instructions

- Inspect the existing design system, route structure, state model, and component
  conventions before making UI changes.
- Preserve NexHaat's established 3D direction, color palette, typography, branding,
  and layout language. Do not redesign by default.
- Build accessible, responsive interfaces with semantic HTML, keyboard support,
  visible focus, labels, and useful validation feedback.
- Treat client-side state as presentation state, never as proof of authorization,
  payment success, inventory availability, or final price.
- Do not put secrets, privileged API keys, or authorization decisions in browser code.
- Keep loading, empty, error, retry, and success states explicit.
- Avoid unnecessary global state, duplicate components, layout shifts, and large
  client-side bundles.
- Respect reduced-motion settings; 3D effects must not block essential task completion.
- Inspect all changed views at mobile and desktop widths where browser tooling exists.
- Add or update tests using the project's actual test framework; do not invent scripts.
