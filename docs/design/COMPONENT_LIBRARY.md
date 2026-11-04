# Component library map

This is an implementation map for the repository's existing components, not a replacement component framework.

| Component family | Existing source | Signature Blue treatment |
|---|---|---|
| Brand mark and lockup | `public/logo.svg`, `app/static/logo.svg`, `Navbar.tsx`, shared Flask header | Original N/orbit mark in blue, sky and navy; preserve local sizes and motion |
| Global navigation/search | `src/components/Navbar.tsx`, Flask `base.html` and `site.css` | Navy structure, active Blue state, blue search focus, visible theme toggle |
| Primary/secondary actions | Existing Tailwind buttons and Flask marketplace buttons | Blue primary with white text; white/navy secondary; orange reserved for promotions |
| Product cards | React product components, Flask `.product-card` and `.trending-card` | Clean white/dark navy surfaces, navy text, blue hover/focus, green only for success |
| Forms and validation | React form pages, Flask `.form-field`, auth CSS | Blue focus frame; error red; labels, descriptions and server errors remain visible |
| Notifications/toasts | React `Toast`, Flask notifications and flash messages | Blue information state, orange warning accent, green success, red error |
| Portals and analytics | Seller/Admin/Rider portal pages and Flask dashboards | Navy structure, blue active/progress/data accents, restrained orange highlights |
| Empty/loading/error states | Current page components and shared styles | Keep truthful preview/unavailable/error copy; blue skeleton/focus accent without implying a successful request |
| Android controls | Compose Material 3 components | Shared palette through `MaterialTheme`; existing navigation, DTOs and state flows stay intact |

Keep semantic success, warning and danger tokens separate from the brand primary. Any new shared component should reuse the closest existing family and include keyboard focus, label and narrow-screen behavior.
