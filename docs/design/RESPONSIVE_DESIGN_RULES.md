# Responsive and interaction rules

- Preserve the current layout system. Flask CSS has breakpoints at 1000, 720, 560 and 400 px and supports a 320 px minimum page width. React continues to use existing Tailwind breakpoints and mobile navigation. Android keeps native Compose sizing and insets.
- At narrow widths, keep search and primary shopping actions reachable, allow content/cards to wrap, and avoid horizontal page overflow. Do not shrink tap targets below existing accessible control sizes to fit a header.
- Keep the logo/name, active navigation, account, order, cart and theme actions understandable when labels collapse; use accessible names for icon-only controls.
- Keyboard users must see the blue focus ring and be able to reach menus, dialogs, search suggestions, form errors and primary actions in a logical order. Do not use hover as the sole activation path.
- Respect `prefers-reduced-motion` on web and Android system motion settings. Keep existing 3D card motion disabled for reduced motion and avoid blocking interaction while sections animate.
- Light/dark mode must preserve readable contrast, selected states, validation messages, product prices and destructive-action labels. Orange badges use dark text; green remains success-only.
- Verify loading, empty, preview/unavailable, network-error, invalid-input and server-rejection states separately from successful persisted records.

The shared identity change does not replace the outstanding full keyboard, screen-reader, device, slow-network and responsive acceptance audit recorded in the implementation tracker.
