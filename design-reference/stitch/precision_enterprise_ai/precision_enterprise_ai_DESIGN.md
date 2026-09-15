---
name: Precision Enterprise AI
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a77'
  outline-variant: '#bcc9c6'
  surface-tint: '#006a61'
  primary: '#00685f'
  on-primary: '#ffffff'
  primary-container: '#008378'
  on-primary-container: '#f4fffc'
  inverse-primary: '#6bd8cb'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#006194'
  on-tertiary: '#ffffff'
  tertiary-container: '#007bb9'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#89f5e7'
  primary-fixed-dim: '#6bd8cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#005049'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-sm:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system targets customer experience directors, operations leads, and tier-3 support engineers operating in high-volume, enterprise e-commerce environments. The system balances operational density with cognitive clarity, rejecting visual noise in favor of immediate situational awareness, rapid triaging, and trustworthy AI orchestration.

The visual direction follows **Corporate / Modern** execution with technical utility:
- **Tone:** Methodical, surgical, dependable, and calm under operational stress.
- **Visual Stance:** Structured canvas architecture utilizing deep navy navigation chrome contrasted against light, high-legibility workspace surfaces. AI indicators are restrained and deliberate, avoiding mystical tropes in favor of clear status, confidence scores, and predictable deterministic interfaces.
- **Key Principles:**
  - *Zero Ambient Distraction:* Eliminates heavy glow effects and decorative gradients to maintain low eye fatigue across 8-hour agent shifts.
  - *Data-First Legibility:* Monospaced tabular figures, clear operational hierarchy, and explicit delineation between automated agents and human participants.
  - *Hairline Precision:* Structured structural division through subtle neutral borders rather than diffuse drop shadows.

## Colors

The palette establishes a clear structural dichotomy between high-contrast navigation framing and dense, high-readability content work areas.

### Role Tokens & Distribution
- **Primary (`#0d9488` / `#14b8a6`):** Dedicated to active AI interactions, synthetic generation indicators, primary execution buttons, and machine confidence tokens.
- **Secondary (`#0f172a` / `#1e293b`):** Deployed across fixed global navigation, collapsed application drawers, contextual command palettes, and primary header text.
- **Tertiary (`#0284c7`):** Signals active AI reasoning streams, queued background automation, and synthetic ticket parsing runs.
- **Neutral (`#64748b` base):**
  - Surface Background: `#f8fafc` (Canvas / App background), `#f1f5f9` (Subtle track / Table header wells).
  - Surface Cards: `#ffffff` (Zero-tint white for data cards and inspection panels).
  - Hairline Borders: `#e2e8f0` (Default panel boundaries and list separators).
  - Text: `#0f172a` (Primary typography), `#475569` (Secondary labels and metadata), `#94a3b8` (Muted/Disabled).

### Status System
- **Emerald (`#10b981`):** Resolved tickets, healthy model throughput, automated SLA compliance.
- **Amber (`#f59e0b`):** Pending human takeover, low-confidence bot responses, SLA warnings.
- **Rose (`#ef4444`):** SLA breaches, sentiment escalation, automated workflow failures.
- **Sky / Cyan (`#0284c7` / `#06b6d4`):** Active real-time AI generation and incoming customer webhooks.

## Typography

The type system prioritizes micro-legibility at enterprise density. Font scales remain compact and tightly metered to avoid pushing operational data beneath the fold.

- **Typeface:** Inter handles all typographic levels, configured with OpenType features (`cv02`, `cv03`, `cv04`, `cv11`) enabled to maximize character disambiguation between `I`, `l`, and `1`.
- **Numerical Alignment:** All metric widgets, conversation timers, confidence percentages, and ticket IDs must enforce OpenType tabular figures (`tnum`) and slashed zeros (`zero`).
- **Hierarchy Rules:** 
  - Standard ticket detail headers must never exceed `headline-md` (1.25rem).
  - Conversation bubbles strictly use `body-md` (0.875rem) at 1.25rem line height for compact parsing.
  - Meta tags, confidence chips, and timestamp indicators map to `label-md` and `label-sm` with slight positive tracking to ensure legibility when set against muted backgrounds.

## Layout & Spacing

The layout is built on a 3-pane responsive desktop shell:
1. **Global Chrome (Left):** 64px collapsed icon rail or 240px expanded navigation menu in deep navy (`#0f172a`).
2. **Ticket Triage Queue (Center-Left):** 360px–420px list column with zero page margin, utilizing a fluid scrollable stack.
3. **Workspace Canvas (Center-Right):** Primary split conversation thread and customer profile inspector, filling remaining horizontal space via a dynamic flex container.

### Breakpoints & Adaptive Reflow
- **Desktop (1280px+):** Full 3-pane arrangement. Center and right panes exist concurrently without overlay drawers.
- **Tablet / Small Laptop (1024px - 1279px):** Customer profile moves into an off-canvas drawer triggered by a persistent right tab; triage queue and workspace share the viewport.
- **Mobile (< 1023px):** Single-pane layout with view switches managed via unified bottom navigation. Triage queue, conversation thread, and customer telemetry stack sequentially.

### Spacing Cadence
Component internals follow an absolute 4px/8px baseline grid:
- `space-xs` (4px): Micro-gaps between badge status dots and text labels.
- `space-sm` (8px): Gaps between action icons in toolbar strips and internal input field padding.
- `space-md` (12px): Standard message bubble padding and compact list row vertical rhythm.
- `space-lg` (16px): Card inner padding and separator rhythm across dashboard panels.
- `space-xl` (24px): Major module segregation across the analytical workspace.

## Elevation & Depth

Visual depth is achieved through **low-contrast outlines** complemented by precise, micro-diffused ambient shadows. High-elevation blur spreads and heavy drop shadows are prohibited to maintain a crisp operational toolset.

### Surface Tiers & Hairline System
- **Level 0 (App Canvas):** Flat `#f8fafc` background with no elevation.
- **Level 1 (Structured Panels & Base Cards):** `#ffffff` solid fill enclosed by a continuous 1px solid border (`#e2e8f0`). No drop shadow in resting state.
- **Level 2 (Dropdowns, Tooltips, Action Popovers):** `#ffffff` fill, 1px solid border (`#cbd5e1`), accompanied by an ambient shadow: `0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 2px 4px -1px rgba(15, 23, 42, 0.04)`.
- **Level 3 (Modal Dialogs & Emergency Overlays):** `#ffffff` fill, framed with a 1px border (`#94a3b8`), raised with `0 12px 24px -4px rgba(15, 23, 42, 0.12), 0 4px 8px -2px rgba(15, 23, 42, 0.04)`. Accompanied by a 40% opacity slate backdrop (`rgba(15, 23, 42, 0.4)`).

### Active States & Border Shifts
Interactive components rely on 1px chromatic border transitions rather than positional elevation changes. A hovering interactive card transitions border color from `#e2e8f0` to `#cbd5e1` with zero pixel translation. Active focus rings leverage a dual-ring setup: `0 0 0 1px #ffffff, 0 0 0 3px rgba(13, 148, 136, 0.3)`.

## Shapes

The design system enforces balanced geometric structure. It steers clear of fully brutalist hard rectangles and avoids overly bubbly consumer forms, settling on measured enterprise contours.

- **Inputs, Buttons, and Chat Bubbles:** 0.5rem (8px) radius matches the visual density of the type scale.
- **Containers, Table Shells, and Modals (`rounded-lg` / `rounded-xl`):** 0.75rem (12px) for primary analytical cards and thread viewports.
- **Badges, Confidence Tags, and Avatars:** Fully rounded pill shapes (`9999px`) ensure rapid shape recognition, segregating system metadata tags from rectangular actionable controls.

## Components

### 1. Buttons & Controls
- **Primary Action (AI / Dispatch):** Background `#0d9488`, text `#ffffff`, border transparent. Hover: `#0f766e`. Active: `#115e59`.
- **Secondary Neutral:** Background `#ffffff`, text `#0f172a`, border 1px solid `#e2e8f0`. Hover: `#f8fafc`, border `#cbd5e1`.
- **Dark Navigation Utility:** Deep navy chrome interactions set against `#1e293b` with `#94a3b8` icons, transitioning to `#ffffff` icon fill and `#334155` background on hover.
- **Button Sizing:** Strict 32px height for inline workspace actions (padding: 0 12px, font-size: 0.875rem); 40px height for primary triage forms.

### 2. Form Inputs & Search Fields
- Single-line inputs and filters feature a crisp `#ffffff` background with a 1px border of `#cbd5e1`. 
- Placeholder text is set to `#94a3b8`.
- Focus states apply a 1px border of `#0d9488` with a 3px ambient ring of `rgba(13, 148, 136, 0.15)`.

### 3. Actor-Differentiated Message Bubbles
Conversation streams must instantly distinguish the origin of every entry:
- **Customer Bubble:** Left-aligned. Fill: `#f1f5f9`. Border: 1px solid `#e2e8f0`. Text: `#0f172a`. Avatar: Circular photo or neutral initials tag (`#cbd5e1` fill with `#475569` glyph).
- **Human Agent Bubble:** Right-aligned. Fill: `#ffffff`. Border: 1px solid `#cbd5e1`. Text: `#0f172a`. Avatar: Circular photo with an explicit blue badge dot (`#0284c7`).
- **AI Assistant Bubble:** Left-aligned with distinctive full-width machine card treatment. Fill: `#ffffff`. Border: 1px solid `#ccfbf1`. Left visual anchor: 3px solid teal accent border (`#0d9488`). Avatar: Teal square-rounded container (`#f0fdfa`) framing the machine intelligence emblem (`#0d9488`).
- **Metadata Footer:** Attached to each message at `label-sm` in `#64748b`, including delivery timestamps and explicit bot confidence metrics (e.g., `Confidence: 98.4% · Grounded via Order API`).

### 4. Data Tables & Ticket Rows
- **Table Head:** `#f8fafc` background with a 1px bottom border `#e2e8f0`. Labels in `label-sm` (`#64748b`), uppercase with `0.05em` tracking.
- **Table Body:** Zero stripe alternations; pure white rows with 1px bottom hairpins (`#f1f5f9`). Hover state updates row background to `#f8fafc`.
- **Numeric Cells:** Explicit tabular numeric styling with right alignment for order values, response latencies, and resolution times.

### 5. Badge Pills & Status Indicators
Badges use micro-pill geometries (`rounded-full`, height: 22px, padding: 2px 8px) with 1px tone-on-tone borders:
- **AI Active / Generated:** Background `#f0fdfa`, border `#99f6e4`, text `#0f766e`.
- **Pending Escalation:** Background `#fffbeb`, border `#fde68a`, text `#b45309`.
- **Resolved:** Background `#ecfdf5`, border `#a7f3d0`, text `#047857`.
- **Critical SLA Breach:** Background `#fef2f2`, border `#fecaca`, text `#b91c1c`.

### 6. Specialized System Components
- **Confidence Meter Bar:** Inline micro-progress component (4px height, track `#e2e8f0`) utilizing primary teal for scores >90%, transitioning to amber for scores between 70% and 89%, and rose for scores below 70%.
- **Context Drawer Cards:** Hairline modular panels displaying live e-commerce shipping tracking, customer lifetime value, and order logs, segmented with `#f8fafc` label headers and `#ffffff` content wells.