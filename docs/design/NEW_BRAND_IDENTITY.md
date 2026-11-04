# NexHaat Signature Blue identity

## Brand idea

NexHaat is a Bangladesh-first marketplace with its own recognizable mark: the existing custom N letter set inside a blue rounded tile, crossed by an orbital stroke. The mark remains original NexHaat artwork; the current task recolors that mark with the permanent Signature Blue palette instead of adopting another marketplace's identity.

## Palette hierarchy

| Token | Hex | Role |
|---|---|---|
| NexHaat Blue | `#1769FF` | Primary brand, links, active states, focus, progress and primary actions |
| Deep Navy | `#0B1F3A` | Professional navigation, headings, logo depth and structure |
| Sky Blue | `#4D91FF` | Secondary blue, dark-theme links and subtle highlights |
| Light Blue | `#EAF2FF` | Selected surfaces, soft focus context and supporting panels |
| Amazon Orange | `#FF9900` | Limited promotion, cart and offer accents |
| Daraz Orange | `#F85606` | Optional secondary campaign accent, used sparingly |
| Alibaba Red | `#E1251B` | Error/destructive state only |
| White | `#FFFFFF` | Product and content surfaces |
| Soft Gray | `#F3F4F6` | Light page canvas |

Green remains reserved for success/positive status. Orange does not become a second primary color; red is not used as decoration.

## Identity use

- Web Vite logo is `public/logo.svg`; Flask serves `app/static/logo.svg`. They preserve the N/orbit silhouette and use the same palette.
- Flask and React share the supplied brand tokens; Android Material theme uses the same light/dark roles.
- Brand blue is used for buttons, selected navigation, search/focus, analytics accents, notification feedback and loading progress where components consume the shared tokens.
- Dark theme pairs blue/sky accents with Deep Navy surfaces and high-contrast text.

This palette is a design override requested for OMEGA. It does not change commerce rules, data authority, or canonical release status.
