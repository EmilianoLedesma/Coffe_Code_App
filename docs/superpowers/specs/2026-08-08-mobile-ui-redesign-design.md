# Mobile UI Redesign — Design Spec

**Date:** 2026-08-08
**Author:** brainstorming session with user
**Status:** approved by user via clarifying questions (color direction, scope, navigation, dark mode); design body below written and self-reviewed, proceeding per user's explicit "do not stop" directive for this session.

## Goal

Coffee Code's mobile app (React Native/Expo, 15 screens across Mesero/Cocina/Caja roles) currently has zero design system: every screen defines its own inline `StyleSheet`, colors are ad-hoc (at least 4 near-identical greys, string literals like `'red'` mixed with hex equivalents), no shared components, no icon library, plain system font. The user wants a modern visual redesign before doing real device testing, using a reference project (`SWAY POO/MockupsSwayMobile`) as the structural/geometric inspiration — NOT its literal color palette.

## Reference analysis (Sway)

Sway is an Apple-HIG-inspired design language: iOS-blue primary on a near-black/gray text scale over an off-white canvas with white cards, generously rounded geometry (12-20px on cards/buttons, 999px pill chips/badges), soft low-opacity tinted shadows (including a brand-colored glow shadow under primary CTAs), Ionicons in outline (inactive) / filled (active) pairing, uppercase letter-spaced "eyebrow" form labels, negative letter-spacing on bold headlines, and one consistent "selected state" grammar (tint background + colored border + colored bold text) reused across chips, filters, and form pickers. Full detail captured in the recon findings this session; not duplicated here — this spec adapts that language with a coffee-appropriate palette, per user decision.

## Decisions locked in (from clarifying questions)

1. **Color**: coffee brand palette (espresso brown primary, cream canvas), not Sway's blue. Keep Sway's structural language (radii, shadows, chip grammar, header pattern).
2. **Scope**: all 15 screens redesigned in one pass, not a role-by-role pilot.
3. **Navigation**: keep the existing single stack navigator (no bottom tabs, no new nav dependency) — pure visual restyle of headers/transitions, zero navigation-logic change.
4. **Dark mode**: light-only, matching Sway (which also has none).

## Design tokens (`mobile/theme/`)

### `colors.js`

| Role | Hex |
|---|---|
| Primary (espresso) | `#3C2415` |
| Primary pressed/dark | `#2A1810` |
| Primary tint bg (chips/badges) | `rgba(60,36,21,0.08)` |
| Secondary accent (caramel) | `#C77D33` |
| Secondary tint bg | `rgba(199,125,51,0.10)` |
| Canvas background | `#FAF6F1` |
| Surface (cards/inputs/modals) | `#FFFFFF` |
| Text primary | `#2B1B12` |
| Text secondary | `#8A7968` |
| Text tertiary (placeholder/disabled) | `#C4B8AB` |
| Border subtle | `rgba(43,27,18,0.08)` |
| Border visible/divider | `#E4DACD` |
| Success (Libre / Entregado) | `#2E7D4F` (bg tint `#E8F5EC`) |
| Warning (Reservada / En preparación) | `#C87F0A` (bg tint `#FDF3E2`) |
| Danger (Ocupada exit / Cancelado / errors) | `#C0392B` (bg tint `#FBEAE8`) |
| Info (informational labels, e.g. "Cobrado") | `#2E6B8C` (bg tint `#E8F1F5`) |

Maps directly onto the app's existing semantic meanings (Libre=green, Reservada=amber, Ocupada/error=red, info=blue) — same meanings, refined/consistent hex values instead of the current ungoverned mix.

### `typography.js`

No custom font loading (matches Sway's platform-adaptive default-font approach — avoids adding `expo-font` complexity for a session with no device to visually verify kerning on). System font, weight-differentiated.

- Size scale: `xs:11 sm:12 md:14 lg:15 xl:17 xxl:22 hero:28`
- Weight scale: `regular:400 medium:500 semibold:600 bold:700 extrabold:800`
- Headlines: bold/extrabold, letterSpacing `-0.3` to `-0.5`
- Eyebrow labels (form field labels, section headers): uppercase, semibold, 11-12px, letterSpacing `+0.5`

### `spacing.js`

- Spacing scale (px): `4, 8, 12, 16, 20, 24, 32, 40`
- Radii: `r8:8` (small chips) `r12:12` (buttons, inputs, standard cards) `r16:16` (modals) `r20:20` (hero/feature cards) `r999:999` (pills)
- Shadows: `xs` (list-item cards, opacity 6%, radius 3) `sm` (buttons/light modals, opacity 7%, radius 10) `md` (prominent cards/modals, opacity 10%, radius 20). Primary CTA buttons additionally get a brand-tinted glow shadow (`shadowColor: colors.primary, shadowOpacity: 0.25`).

## Shared components (`mobile/components/`)

One file per component, each a thin `View`/`TouchableOpacity` wrapper reading from `theme/`:

- **`Button.js`** — variants `primary` (solid espresso fill + glow shadow), `secondary` (dashed espresso border, transparent fill — Sway's "add new" pattern, reused here for "Nuevo pedido"/"Nueva categoría" style actions), `text` (plain colored label, no container). Props: `variant`, `label`, `onPress`, `disabled`, `loading`.
- **`Card.js`** — white surface, `r12` default (`r20` via a `size="hero"` prop for feature cards like MesasScreen's table tiles), `shadows.xs`. Wraps arbitrary children.
- **`Input.js`** — bordered `r12` text input with an eyebrow-style label above it. Props: `label`, `value`, `onChangeText`, `placeholder`, `keyboardType`, `error` (renders the Sway-style light-red error banner beneath).
- **`Badge.js`** — pill-shaped status indicator: color dot + label. Used for pedido/mesa/cocina status everywhere (`Pendiente/En preparación/Listo/Entregado/Cancelado`, `Libre/Ocupada/Reservada`). Props: `label`, `tone` (maps to a semantic color).
- **`Chip.js`** — selectable pill (category filters in MenuScreen, ingredient picker in GastosScreen's compra card). Active state = tint bg + colored border + colored bold text (Sway's consistent selected-state grammar). Props: `label`, `selected`, `onPress`.
- **`ListItem.js`** — generic row: leading icon/avatar slot, title, subtitle, trailing content slot (badge/chevron/action buttons). Replaces the 14x independently-implemented `FlatList` row card.
- **`ScreenHeader.js`** — optional in-screen header block (title + subtitle + back/action icon buttons) for screens wanting more than the native stack header provides (e.g. a subtitle under the title). Native stack header (already restyled via `App.js` `screenOptions`) covers the simple case.
- **`EmptyState.js`** — icon + message, for empty lists (no pedidos in cola, no ingredientes, etc).

## Icons

Install `@expo/vector-icons` (ships with Expo SDK, zero new native dependency — already a transitive dependency of `expo`, just needs importing) → `Ionicons`. Replaces the current text-symbol icons (`+`, `✔`, `←`) app-wide. Convention: `-outline` for default/inactive, filled for active/selected — mirrors Sway exactly. Concrete mapping (non-exhaustive, finalized during implementation): mesa tiles get `restaurant-outline`/`restaurant`, cart/pedido gets `receipt-outline`, cocina gets `flame-outline`, caja gets `cash-outline`, back buttons get `chevron-back`, add actions get `add-circle-outline`, delete gets `trash-outline`, stock alerts get `warning-outline`.

## Screen-by-screen scope

All 15 screens get their `StyleSheet.create` block replaced with the shared theme tokens/components. This is a **pure visual restyle** — no navigation logic, no data-fetching logic, no state-management changes in any screen. Every existing `useFocusEffect`, WS subscription (`DetalleScreen`/`ColaPedidosScreen`/`CajaScreen`, from the just-completed Fase 4 work), API call, and role-gate stays untouched; only the returned JSX's styling/markup changes to use the new components.

Grouped by natural SDD task boundaries (final task breakdown happens in the implementation plan, not here):
- **Foundation**: `theme/` + `components/` + Ionicons install + `App.js` stack header restyle (`screenOptions`).
- **Shared/auth screens**: Splash, Login, RecuperarPassword, Home.
- **Mesero**: Mesas, Pedido, Detalle.
- **Cocina**: ColaPedidos, CocinaDetalle, Cocina (home), Menu, Inventario.
- **Caja**: Caja, Pago, Gastos.

## Non-goals (explicit, to prevent scope creep)

- No bottom-tab navigation restructure (decided: keep stack).
- No dark mode (decided: light-only).
- No custom font loading.
- No new UI kit/library dependency beyond `@expo/vector-icons` (already effectively free).
- No change to any screen's data logic, API calls, or WebSocket subscriptions — visual layer only.
- No new backend/API changes.

## Verification approach

No physical device/Expo Go available this session (same constraint as the WebSocket work). Verification is therefore:
1. **Static correctness per task**: JSX/braces balance, no undefined component/prop references, theme token names resolve to real exports, no orphaned old-style inline colors left behind accidentally.
2. **Structural consistency review**: task reviewer confirms each screen actually uses the shared components/tokens rather than reinventing local styles (the whole point of this redesign), and that no screen's non-visual logic changed.
3. **Explicitly deferred to the user**: real visual QA (does it look good, are touch targets comfortable, does text wrap correctly on a real screen size) happens when the user runs Expo Go on a device — this spec's own review loop cannot substitute for that, and per the user's session-level instruction, review steps that depend on seeing a live rendered frontend are skipped here by design, not by oversight.

## Risks / open items carried into planning

- 15 screens is a lot of surface area for one plan — the implementation plan (next step) should size tasks so no single task both builds a shared component AND migrates many screens onto it; foundation work must land and be reviewed before any screen migration task starts.
- `ListItem`/`Card` need to flex enough to cover fairly different real layouts (a 2-column mesa grid tile vs. a full-width pedido queue row vs. a form card) — the component API should stay generic (slots, not screen-specific props) rather than growing screen-specific special cases.
- Icon-mapping table above is a starting point, not exhaustive — implementation tasks may need to pick reasonable additional icons for cases not enumerated here; task briefs should say so explicitly rather than let an implementer guess silently.
