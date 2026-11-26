---
name: ORCIA
title: ORCIA — Visual Identity & Design System (Direction C : Enterprise Adaptive Hybrid)
status: draft
created: 2026-10-24
updated: 2026-11-25
description: Human-Led, Agent-Accelerated enterprise and personal process execution platform built on shadcn/ui (Radix + Tailwind CSS) with Direction C Sobriety 4-Zone layout (Left Sidebar with single Active Space selector, 9 navigation entries & bottom-left My Account popover + TopHeaderBar with [O] ORCIA › Screen, Breadcrumb, Search, Notifications & Help + Clean Central Canvas + Right Zone 4 Contextual Help Column).
colors:
  sidebar-bg: '#FFFFFF'
  sidebar-foreground: '#0F172A'
  sidebar-muted: '#64748B'
  sidebar-border: '#E2E8F0'
  sidebar-active-bg: '#EFF6FF'
  sidebar-active-fg: '#2563EB'
  background: '#EAF2FB'
  surface: '#FFFFFF'
  dock-bg: '#FFFFFF'
  foreground: '#0F172A'
  muted-foreground: '#475569'
  border: '#E2E8F0'
  primary: '#2563EB'
  primary-foreground: '#FFFFFF'
  primary-dark: '#6366F1'
  human-led: '#6D28D9'
  human-led-bg: '#F5F3FF'
  arbitration-amber: '#D97706'
  arbitration-bg: '#FFFBEB'
  gate-pass: '#059669'
  gate-pass-bg: '#ECFDF5'
  ontology-cyan: '#0284C7'
  ontology-bg: '#F0F9FF'
  stale-danger: '#DC2626'
  stale-bg: '#FEF2F2'
typography:
  sans:
    fontFamily: 'Inter, Geist Sans, system-ui, sans-serif'
    fontSize: 13.5px
    lineHeight: '1.5'
  display:
    fontFamily: 'Inter, Geist Sans, system-ui, sans-serif'
    fontSize: 22px
    fontWeight: '700'
    lineHeight: '1.25'
  mono:
    fontFamily: 'JetBrains Mono, Geist Mono, monospace'
    fontSize: 12px
rounded:
  sm: 6px
  md: 10px
  lg: 14px
  full: 9999px
spacing:
  sidebar-expanded: 240px
  sidebar-collapsed: 72px
  dock-width: 340px
components:
  sidebar-nav-item-active:
    background: '{colors.sidebar-active-bg}'
    foreground: '{colors.sidebar-active-fg}'
    radius: '{rounded.md}'
  human-led-anchor-card:
    background: '{colors.human-led-bg}'
    border: '1px solid {colors.human-led}'
    borderLeft: '4px solid {colors.human-led}'
    radius: '{rounded.lg}'
  arbitration-tiebreak-card:
    background: '{colors.arbitration-bg}'
    border: '1px solid {colors.arbitration-amber}'
    borderLeft: '4px solid {colors.arbitration-amber}'
    radius: '{rounded.lg}'
  review-briefing-grid:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    radius: '{rounded.lg}'
  uri-badge:
    fontFamily: '{typography.mono.fontFamily}'
    radius: '{rounded.sm}'
---

## Brand & Style

**ORCIA** embodies the **"Human-Led, Agent-Accelerated"** posture through **Direction C Sobriety (4-Zone Architecture)**. Its visual identity relies on four complementary zones that eliminate cognitive overload, raw Unicode emoji clutter, and internal infrastructure jargon:

1. **Zone 1 — Left Scope & Global Navigation Sidebar (`240px` expanded / `72px` collapsed rail via `[`)**:
   - **Top** *(without duplicating `[O] ORCIA`, which lives exclusively in `TopHeaderBar`)*: **Single Active Space Selector** grouped by **`Personal`** + **`Team / Division (BU)`**, synchronized across all primary views (`Cockpit`, `My Assistant`, `My Processes`, `My Agents`, `My Spaces`, `FinOps`).
   - **Center**: **9 Fixed Unnumbered Navigation Entries** (rendered with monochrome `<OrciaIcon />` wireframe SVGs; no "New discussion" button in the sidebar):
     - **`Cockpit`** (Active scope overview, unified 6-step onboarding checklist while `< 6/6`, priority human decisions only when pending items exist — max 3 surface blocks).
     - **`My Assistant`** (Conversational AI workspace active as soon as a chat model is configured, with `+ New conversation` & `Assistant settings` header actions, 3 tabs `Active discussion | Saved (N) | Folders (N)`, verified `[S1]`/`[G1]`/`[O1]` citations, and speed/effort selector).
     - **`My Processes`** (Unlocked once `1` AI model is active; `Validations & Runs | Business Processes | Value Stream` tabs across Focus Review and Studio).
     - **`My Agents`** (`Space Assistant` pinned card, `@handle` specialized agents configured in 6 governed blocks, `/skill` catalog, and `Tool Servers & MCP`).
     - **`My Spaces`** (Single active-workspace view structured in 5 unnumbered tabs: `Onboarding & Overview | Documents & Sources | Deliverables & Artifacts | Glossary & Business Rules | Members & Space Settings`, including automatic `PRIVATE_USER` personal workspace).
     - **`My Organization`** (`/organization`, directly under `My Spaces`, visible to all authenticated users: read-only org tree for standard members, scoped unit creation and member invitations according to `can_*` grants for Division/Team Leads and Admins).
     - **`FinOps`** (Scope bar `This Space | This Team / BU | Platform Base` strictly filtered by user permissions).
     - **`Administration`** (Restricted to `PLATFORM_ADMIN` / `SECOPS`, strictly **5 tabs**: `Accounts & Permissions`, `Authentication`, `AI Models`, `Connectors`, `Business Packs`).
     - **`Help`** (Full-width Help Center with direct `Documentation` showcase link and screen guides).
   - **Bottom-Left Footer**: **Canonical `My Account` / `Mon Compte` Anchor** (`SidebarAccountPopover` + 5-tab `UserSettingsModalDialog`: `Preferences & Display`, `Profile & Security`, `Personal Connections`, `IDE & MCP Keys`, `About / Session`). Account management lives exclusively in the bottom-left sidebar footer and never duplicates inside `TopHeaderBar`.

2. **Zone 2 — Top Header Bar (`TopHeaderBar`, `#FFFFFF`, height `56px`)**:
   - **Left**: Clickable **`[O] ORCIA › <Screen>`** logo returning to `/cockpit`, followed by the clickable scope **`Breadcrumb`**.
   - **Right**: **Contextual Federated Search Trigger (`⌘K` / `Ctrl+K`)**, **`Notifications`** bell, and **`Help` / `Aide`** toggle button (opens/closes the Zone 4 right contextual help column; disabled/marked when already on `/help`). No floating `ⓘ` icons appear in main card headers, and no duplicate user account dropdown lives in `TopHeaderBar`.

3. **Zone 3 — Clean Central Workspace (`1fr`, min `680px`, padding `24px`)**:
   - **Cockpit**: Maximum 3 surface blocks; no empty "No pending decisions" filler banners.
   - **Business Screens**: Standardized onto `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />`. Creation forms open in dedicated modals (`OrciaDialog`) triggered by a single primary header action (`.orcia-ds-btn-primary`). Loading states use `<OrciaSpinner />` and errors render in accessible `[role="alert"]` banners.

4. **Zone 4 — Integrated Right Contextual Help Column (`340px`, collapsible via `Help` or `]`)**:
   - Automatically open while an onboarding screen has `total == 0` (and collapsed by default on `< 1440px` once `total >= 1`), toggleable anytime from the TopBar **`Help`** button.
   - Always renders the **4 canonical pedagogical blocks above the fold** (followed by route-specific targeted sections):
     1. **What this screen is for** (`summaryWhatFor`)
     2. **`IN N STEPS` / `EN N GESTES`** (numbered action steps)
     3. **`A REAL EXAMPLE` / `UN EXEMPLE RÉEL`** (amber-framed concrete scenario)
     4. **`COMMON PITFALLS` / `CE QUI COINCE SOUVENT`** (actionable troubleshooting bullets).

### Five Fundamental UI Rules (Invariant Pillars)

1. **Visual Hierarchy**: Guide attention with typography scale, contrast, spacing, and weights (`400`, `500`, `600`, `700`) separating page identity, primary CTA, KPI counters, and secondary metadata.
2. **Maximum Two Font Families**:
   - **Primary (`Inter` / `Geist Sans`)**: All UI copy, headings (`display`), and document reading.
   - **Secondary (`JetBrains Mono` / `Geist Mono`)**: Technical identifiers, federated URIs, `SHA-256` fingerprints, keyboard hints (`⌘K`, `[`, `]`), and RFC 9457 error codes.
3. **Graphical Consistency & Monochrome Icons (`<OrciaIcon />`)**: Every icon across `@orcia/ui` and `apps/web` renders a monochrome wireframe `<svg>` (`currentColor`, `strokeWidth={1.75}`) from `ORCIA_ICONS` (`packages/ui/src/components/icons/`). **Zero raw Unicode emojis (`🤖`, `🛠️`, `🔌`, `🔒`, `📁`, `📦`, `⚠️`, `✅`, etc.) are permitted in headers, tabs, buttons, badges, cards, or scope selectors.**
4. **Grid & Alignment**: Regular `8px`/`16px`/`24px` spacing scale, crisp surfaces, and zero-CLS tab strips.
5. **Contrast & Accessibility (WCAG 2.2 AA)**: Normative contrast ratios (`>= 4.5:1` body text, `>= 3:1` large headings and UI controls) in both light and dark modes, full keyboard navigation, and complete `fr` / `en` bilingual parity.

### User-Centric Microcopy & Bilingual Parity (`fr` / `en`)

- **Zero Internal Plumbing Jargon**: UI dictionaries (`fr`/`en`) adopt strictly the business user's perspective. Internal implementation terms (`DBOS`, `PostgreSQL 18`, `pgvector`, `halfvec`, `Outbox`, `Wasmtime`, `Starlark`, `Argon2id`, `OIDC PKCE`, `Passthrough`, `Tie-Break`, `Rubber-stamping`, `What-If`, `RFC 9457`, raw `team_default` keys, `Temp 0.2 · 4096 tok`, or `(Skills)` in French labels) must never leak into user-facing screens.
- **Human-Readable Settings & Proper Pluralization**: Agent model summaries display clean localized labels (e.g. `Par défaut · Précis · Contexte 4k` / `Team default · Precise · 4k context`) and counters respect singular vs plural (`1 actif` vs `N actifs`, `1 réutilisable` vs `N réutilisables`).

## Colors

Semantic colors carry strict governance meaning — never decorative accent noise:

- **Sidebar Crisp White (`#FFFFFF` / Border `#E2E8F0` / Active Pill `#EFF6FF`)**: Clean navigation background separating Zone 1 from the central workspace.
- **Canvas Background (`#EAF2FB` / `#F8FAFC` Light / `#0B0F17` Dark)**: Soft backdrop framing white `#FFFFFF` cards.
- **Primary Cobalt (`#2563EB` Light / `#6366F1` Dark)**: Primary CTA, active sidebar item, and active Assistant presence.
- **Human-Led Violet (`#6D28D9` / Background `#F5F3FF`)**: Reserved exclusively for **Mandatory Human Anchors** (`human_authored_required: true`, `HumanLedAnchorCard`).
- **Arbitration & Challenge Amber (`#D97706` / Background `#FFFBEB`)**: Workflow suspension awaiting human arbitration, Zone 4 *Real Example* callout, or `[STALE_WARNING]` indicator.
- **Gate Pass Emerald (`#059669` / Background `#ECFDF5`)**: Verified Gate, `REFERENCE` source, claimed presence lock, or valid cache state.
- **Ontology Cyan (`#0284C7` / Background `#F0F9FF`)**: Multi-level Glossary / Ontology badges (`[G1]`) and `AutonomousExecutionBadge`.
- **Stale / Blocker Crimson (`#DC2626` / Background `#FEF2F2`)**: Critical ontology conflict, open circuit breaker, Gate failure, or permission block.

## Typography

- **Primary UI & Reading (`Inter` / `Geist Sans`)**:
  - Body & Conversation (`13.5px`–`14px`, `line-height: 1.5`) calibrated for simultaneous Sidebar + Central Canvas + Zone 4 Help visibility.
  - Page Titles & KPI Counters (`display`, `22px`–`28px`, `font-weight: 700`, `line-height: 1.25`, `letter-spacing: -0.02em`).
- **Secondary Provenance & Code (`JetBrains Mono` / `Geist Mono`, `12px`)**: Federated URIs (`orcia://`, `git://`, `confluence://`, `jira://`), citation pills (`[S1]`, `[G1]`, `[O1]`), `SHA-256` digests, and keyboard shortcuts (`⌘K`, `[`, `]`).

## Layout & Spacing

Desktop architecture relies on the **4-Zone Shell (`Direction C`)**:
1. **Zone 1 — Left Sidebar (`240px` expanded / `72px` collapsed rail via `[`)**: Single `Active Space` selector (`Personal` + `Team / Division`), 9 unnumbered navigation items (`Cockpit`, `My Assistant`, `My Processes`, `My Agents`, `My Spaces`, `My Organization`, `FinOps`, `Administration`, `Help`), and bottom-left `My Account` footer (`SidebarAccountPopover` -> `UserSettingsModalDialog`).
2. **Zone 2 — Top Header Bar (`56px`, `#FFFFFF`)**: Left `[O] ORCIA › <Screen>` + clickable Breadcrumb; Right `⌘K` Federated Search, `Notifications`, and `Help` toggle.
3. **Zone 3 — Central Canvas (`1fr`, min `680px`, padding `24px`)**: Unified `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />` layout with modal-based creation flows.
4. **Zone 4 — Right Contextual Help Column (`340px`, `#FFFFFF`, toggleable via `Help` or `]`)**: Auto-open on empty states, 4 canonical blocks rendered above the fold followed by route-matched targeted sections.

On **Mobile Companion (`< 768px`)**, the grid collapses to a single-column layout driven by a 3-item bottom tab bar (`Cockpit`, `My Assistant / Arbitration`, `Decisions`).

## Elevation & Depth

- Structural separation between Sidebar, TopHeaderBar, Central Canvas, and Zone 4 Help relies on crisp surface contrast and `1px solid` borders (`#E2E8F0` light / `#1E293B` dark).
- Interactive cards use subtle elevation (`0 1px 3px rgba(15, 23, 42, 0.04)`).

## Shapes

- `rounded-sm` (`6px`): citation pills (`[S1]`, `[G1]`, `[O1]`), origin badges, and URI badges.
- `rounded-md` (`10px`) & `rounded-lg` (`14px`): `HumanLedAnchorCard`, `ArbitrationTieBreakCard`, `ChunkValidationCard`, and modal dialogs.
- `rounded-full`: filter pills (`.orcia-ds-filter-pill`) and real-time claim/status pills.

## Key Identity Components (`@orcia/ui`)

1. **Sidebar Navigation & Single Space Selector (`GlobalSidebar`, `UnifiedScopeSelector`, `SidebarAccountPopover`)**: Single grouped workspace selector, 9 unnumbered entries with 72px rail mode, and bottom-left `My Account` trigger opening the 5-tab `UserSettingsModalDialog`.
2. **Human-Led Anchor Card (`HumanLedAnchorCard`)**: `4px solid #6D28D9` left border with `human_authored_required: true` header; AI auto-fill is strictly forbidden inside this component.
3. **Cognitive Review Briefing (`ReviewBriefingGrid`)**: 2x2 grid in `My Processes › Runs & Decisions` (*1. Executive Summary*, *2. Key Elements & Cross-Check*, *3. Decisions Made*, *4. Retained Assumptions*).
4. **Chunked Validation Card (`ChunkValidationCard`)**: Section-level validation, co-editing, and upstream challenge/rewind actions.
5. **Arbitration Tie-Break Matrix (`ArbitrationTieBreakCard`)**: Amber decision card for equal-rank trade-offs.
6. **Federated URI & Access Mode Badge (`UriBadge`)**: Monospace URI, role (`REFERENCE` vs `ACTIVE`), access mode, and truncated `SHA-256`.
7. **Presence & Claim Pill (`PresenceClaimPill`)**: Real-time lock indicator (`Claim & Open Review` vs `In progress: [Name]`).
8. **Autonomous Execution Badge & Kill-Switch (`AutonomousExecutionBadge`)**: Cyan/Cobalt styling (never Violet) with emergency stop and 1-click rollback.
9. **Declarative Permission Guard (`PermissionGuard`)**: Enforces `create | read | update | delete | execute | grant` visibility (`passive-lock | disabled | hidden`).
10. **Write-Only Secret Field (`SecretField`)**: Backed by `SecretInput` (`keep | set | clear`) and `SecretStatus` fingerprint without pre-filling masks.
11. **Contextual Help Panel (`ContextualHelpColumnView`)**: Right 340px column rendering the 4 DESIGN.md blocks (`What this screen is for`, `IN N STEPS`, `A REAL EXAMPLE`, `COMMON PITFALLS`) above the fold, followed by route-targeted sections and Ask-Assistant prefill CTA.
12. **Canonical Two-Tier Page Header (`<OrciaPageHeader />`)**: White `.orcia-bento-card` surface with monochrome `<OrciaIcon />`, single semantic `<h1>`, optional `contextBadge`, 1-line `subtitle`, `secondaryActions`, at most **1** solid Cobalt `primaryAction`, Tier 2 `<OrciaTabStrip />` + `scopeBar`, and aligned `alertSlot` directly beneath `<header>`.

## Do's and Don'ts

| Do | Don't |
| :--- | :--- |
| Keep the **9 unnumbered navigation entries** visible in the left Sidebar and place `My Account` (`SidebarAccountPopover`) in the bottom-left Sidebar footer | Number menu entries, duplicate `[O] ORCIA` in the Sidebar, or place user account menus inside `TopHeaderBar` |
| Render monochrome `<OrciaIcon />` SVGs across headers, tabs, cards, buttons, badges, and scope selectors | Leave raw Unicode emojis (`🤖`, `🛠️`, `🔌`, `🔒`, `📁`, `📦`, `⚠️`, `✅`) in production UI copy or headers |
| Render all 4 Zone 4 Contextual Help blocks above the fold (`<HelpCoreNarrativeBlocks />` before `<HelpTargetedSectionsList />`) | Push `What this screen is for` and `IN N STEPS` below targeted sections or route `/organization` to `/settings` help |
| Use Violet `{colors.human-led}` (`#6D28D9`) exclusively for `HumanLedAnchorCard` (`human_authored_required: true`) | Auto-fill human anchor fields with AI or use Violet on autonomous execution badges |
| Display human-readable model settings (`Team default · Precise · 4k context`) and proper singular/plural counters | Expose raw `Temp 0.2 · 4096 tok`, `team_default`, or `(Skills)` jargon inside French UI strings |

## Canonical Page Framing & Visual Grammar (`UH-06`, `UH-07`, Story 29.4)

To eliminate cross-screen header fragmentation and overloaded solid-Cobalt button usage, all primary and secondary ORCIA screens converge on three `@orcia/ui` primitives and a strict three-tier visual grammar:

1. **Canonical Two-Tier Page Header (`<OrciaPageHeader />`, `.orcia-ds-page-header`)**:
   - **Tier 1 (Identity & Primary Action)**: White `.orcia-bento-card` surface (`var(--orcia-surface-card)`, `1px solid var(--orcia-border-subtle)`, `padding: 16px 20px`) containing a monochrome `<OrciaIcon />`, semantic `<h1>` at `var(--font-size-h2)`, optional inline `contextBadge`, concise 1-line `subtitle`, and right-aligned action slots (`secondaryActions` + at most **1** solid Cobalt `primaryAction`).
   - **Tier 2 (Optional Navigation & Scope Bar)**: Separated by a subtle top border (`.orcia-ds-page-header-tier2`), hosting `<OrciaTabStrip />` on the left and contextual `scopeBar` controls on the right so tab-switching never wraps or shifts primary CTAs (`CLS = 0`).
   - **Aligned Alert Slot (`alertSlot`)**: Rendered strictly beneath `<header>` at exact page width (`.orcia-ds-page-header-alert-slot`), never above the header card.
2. **Accessible Horizontal Tab Strip (`<OrciaTabStrip />`, `.orcia-ds-tab-strip`)**:
   - Exposes `role="tablist"` (`aria-orientation="horizontal"`), `role="tab"`, `aria-selected`, optional count badges, monochrome `<OrciaIcon />`, `disabled` / `disabledReason` tooltips, optional `trailingSlot`, and `ArrowLeft`/`ArrowRight`/`Home`/`End` keyboard navigation across enabled tabs.
   - Uses `underline` (default) or neutral `segmented` active styling (`var(--color-tab-strip-active-fg)`, `var(--color-tab-strip-active-indicator)`) — visually distinct from solid Cobalt primary buttons and neutral filter pills.
3. **White Surface Data Card (`<OrciaDataCard />`, `.orcia-ds-data-card`)**:
   - Frames KPI strips, filter bars, tables, lists, and detail panels on the `#EAF2FB` canvas (`var(--orcia-surface-card)`, `var(--orcia-border-subtle)`) with optional header bar (`icon`, `<h2>` `title`, `subtitle`, `metaBadge`, `actions`) and optional `footer`.
4. **Three-Tier Visual Grammar & Disabled Affordance**:
   - **Primary CTAs (`.orcia-ds-btn-primary`)**: Reserved exclusively for at most 1 primary creation/submission action per header or focus action banner; repeated per-row or per-card actions use secondary/subtle styling.
   - **Tabs (`.orcia-ds-tab-strip-item`)**: Underline or neutral segmented tabs dedicated to view switching (e.g. `Validations & Runs` | `Business Processes` | `Value Stream` on `/processes`, defaulting to `Business Processes` with zero badge when `0` pending runs exist).
   - **Filters & Scope Pills (`.orcia-ds-filter-pill`)**: Neutral rounded-full pills (`var(--color-filter-pill-bg)` -> `var(--color-filter-pill-active-bg)`).
   - **Disabled Buttons**: `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` enforce `opacity: 0.48; cursor: not-allowed; pointer-events: none;`, matching `.orcia-ds-btn-primary:disabled` (`0.48`) and `.orcia-ds-btn-danger:disabled` (`0.50`).

## Epic 30 Interaction & Lifecycle Invariants (`UX30-01`..`UX30-16`)

1. **Honest Modal Save & Inline Alerts (`AssistantGovernanceModalAndStudio`, `AgentDetailAndSandboxModal`)**:
   - Every configuration dialog uses explicit bottom-right `<RgaaDialogFooterActions />` (`Cancel` / `Close` + primary Cobalt `Save` with `<OrciaSpinner />` and `<Enter>` submit) with zero keystroke auto-save and zero `display: none` hidden Save buttons.
   - `isDirty` is computed strictly against hydrated server baselines so reverting a field clears `isDirty` and closes cleanly without false warnings; `Saved` confirmation appears only after server persistence succeeds; errors render inside an inline `[role="alert"]` banner inside the active modal dialog.
2. **Focus Review (`/processes/runs/$runId`)**:
   - Separates process execution from `/processes` tabs onto a dedicated 3-zone layout: **Zone 1** sticky `ProcessRunActionBanner` (strictly 1 state-gated primary Cobalt CTA + progressive-disclosure correction popover), **Zone 2** `ProcessRunArtifactPane` (65% desktop width, Markdown + clickable `#L` source inspection), and **Zone 3** `ProcessRunReasoningRail` (35% desktop width, `defaultCollapsedWhenCompleted={true}`).
3. **`DRAFT` vs `ACTIVE` Agent Lifecycle (`Mes Agents`)**:
   - New or duplicated agents start as `DRAFT` (`UNTESTED`), display factual Test Bench status (`UNTESTED | PASSED | FAILED`), stay excluded from `@agent` Assistant mentions, Process delegation, and external MCP exposure (`HTTP 422`), and promote to `ACTIVE` (`PASSED`) only upon passing Test Bench execution.
