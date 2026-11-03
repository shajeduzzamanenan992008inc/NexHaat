# NEXHAAT GLOBAL UI, ANIMATION & FEATURE-PARITY STANDARD

## Rule 1 — Fully Animated Experience
The NexHaat Website and Android Application MUST provide a polished, modern, responsive, and consistently animated user experience across all major user-facing screens and interactions.

## Rule 2 — App Lifecycle Experience
App launch, splash screen, screen entry, navigation, and exit transitions MUST be designed for smooth visual continuity. Use platform-supported lifecycle transitions where appropriate. Avoid unnecessary startup delays or repetitive, intrusive animations.

## Rule 3 — Global Animation Coverage
All applicable screens, navigation elements, buttons, cards, dialogs, forms, loading states, success states, error states, and user interactions MUST provide appropriate visual feedback and transitions.

## Rule 4 — Website–App Feature Parity
Every user-facing marketplace, AI, account, security, shopping, notification, and accessibility feature available on the Website MUST have an equivalent capability in the Android Application, and vice versa, unless an explicitly documented platform limitation or product decision applies.

## Rule 5 — Platform-Appropriate Design
Feature parity MUST NOT require identical layouts. Website interactions MUST use appropriate web conventions, while Android interactions MUST use appropriate native mobile conventions.

## Rule 6 — Unified Backend and Security
Both platforms SHOULD use the same authoritative backend services, identity system, authorization rules, marketplace data, and security policies wherever applicable. Do not introduce duplicate implementations unnecessarily.

## Rule 7 — AI Experience Parity
AI capabilities available on one platform MUST be available on the other through an appropriate shared service or equivalent integration. AI loading, streaming, errors, and completion states MUST be communicated clearly.

## Rule 8 — Performance First
Animations MUST remain lightweight, avoid unnecessary rendering work, and preserve scrolling, navigation, startup, and interaction responsiveness. Avoid excessive blur, particle effects, continuous animations, or other expensive visual effects on low-end devices.

## Rule 9 — Accessibility and User Control
Respect reduced-motion preferences where supported. Preserve readable text, adequate contrast, touch accessibility, keyboard navigation where applicable, and accessible labels. Animation MUST NOT block essential actions.

## Rule 10 — Consistent Design System
Maintain shared design tokens and documented interaction patterns for colors, typography, spacing, elevation, transitions, animation timing, and motion principles. Adapt these tokens to the platform rather than forcing identical implementations.

## Rule 11 — Feature-Parity Tracking
Maintain a Website–Android feature matrix. Every new feature MUST identify its implementation status on both platforms, required backend changes, security implications, tests, and known limitations.

## Rule 12 — Completion and Verification
A feature MUST NOT be considered complete until its relevant functionality, loading and error states, animation behavior, accessibility, performance, and Website–Android parity have been verified. Report untested scenarios honestly.

## Rule 13 — Preserve Existing Functionality
Animation and parity work MUST NOT silently remove existing functionality, weaken authentication or security, expose secrets, or overwrite unrelated user changes.

## Rule 14 — No Fake Functionality
Animations MUST reflect real application states. Do not display fake loading progress, pretend successful authentication, fabricated AI activity, or success animations when the underlying operation has failed.

## Rule 15 — Motion Quality Standard
Use consistent motion principles: clear entrance and exit transitions, natural easing, restrained micro-interactions, meaningful loading feedback, and smooth state changes. Prefer purposeful animation over decorative motion that harms usability.