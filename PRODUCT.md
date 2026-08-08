# Coffee Code — Mobile Staff App

## Register

product — this is an internal operations tool serving three staff roles during live restaurant service, not a marketing surface.

## Users

Three roles, each using the app on a personal or shared phone during an active work shift, standing, often with one hand occupied (carrying a tray, holding a pan):

- **Mesero (waiter)**: walks the floor, takes orders table-side, checks on order status. Needs fast table-status scanning and quick order entry between other physical tasks.
- **Cocinero (cook)**: stands at a kitchen station, checks the app between cooking tasks (hands may be busy/dirty). Needs an unambiguous, glanceable order queue and large, unmissable status-change controls.
- **Cajero (cashier)**: stands at a register, processes payments and expenses with a customer waiting in front of them. Needs the payment flow to be fast and error-resistant (visible totals, no ambiguity about what's already been charged).

Physical scene: a small-to-midsize cafeteria, daytime, mixed natural and indoor lighting (not a dim bar or a 2am ops room) — a real coffee shop back-of-house and front counter. Screens are checked in short bursts (seconds), not sat with and studied.

## Product purpose

Digitizes what was previously manual/paper: table status, order taking, kitchen queue, payment, and basic expense tracking for a small cafeteria. Backend is a FastAPI service (already built and tested); this app is the staff-facing client. Three roles, one shared login flow, role-gated screens.

## Brand / tone

Coffee shop, not a generic SaaS admin panel and not a consumer social app. Warm, grounded, a little artisanal — espresso/cream tones, not corporate blue. Should feel like a tool a small independent café would actually own, not a rebadged enterprise dashboard template. Confident and calm under pressure (peak-hour usage), never cutesy or playful in a way that slows down a cashier mid-transaction.

## Anti-references

- Not iOS-blue / generic Apple-HIG-blue SaaS look (a structural reference project uses that palette; explicitly diverging on color while keeping some of its geometric discipline).
- Not a Material Design admin template (no default MD component look).
- Not neon/dark-mode "tech" aesthetic — this is a light-filled physical space, not a screen-lit ops room.
- Not overly cute/illustrated (no big mascot illustrations, no rounded cartoon iconography) — staff need speed and clarity over personality during a rush.

## Strategic principles

1. **Speed and glanceability over decoration.** Every screen is used in short bursts during active work — status must be readable at a glance (color + icon + text, never color alone), touch targets generous (staff may be moving/distracted).
2. **One coherent system, not per-screen improvisation.** 15 screens currently duplicate ad-hoc styling independently; the redesign's actual product goal is consistency as much as prettiness.
3. **Visual layer only, this pass.** No navigation, data, or business-logic changes — this is restyling existing, working, tested functionality.
