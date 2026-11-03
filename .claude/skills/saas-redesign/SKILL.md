---
name: saas-redesign
description: Redesign the inventory-management Vue 3 client into a modern SaaS-style interface. It replaces the top nav bar in client/src/App.vue with a fixed left sidebar, introduces design tokens (spacing, colour, type, radius, shadow) as CSS custom properties, and restyles every view's cards, tables, buttons, badges, stat tiles and modals to match, without touching logic, data or routes. Use this skill whenever the user asks to modernise, polish, redesign, re-skin or "make professional" this app's UI, to move the navigation to a sidebar or side nav, to fix inconsistent spacing or styling across the pages, or to make it look like a SaaS dashboard, even if they don't say "redesign".
---

# SaaS redesign for inventory-management

The goal is a calm, professional SaaS dashboard: a fixed left sidebar, a slim top header, generous and *consistent* spacing, and one visual language across all views. This is a **visual-only** change. Users and tests depend on the current behaviour, so every route, filter, API call, computed value, i18n key and event must work exactly as before. If you are unsure whether a change is visual, leave it alone.

Expect a large diff: about 19 files and roughly 3,000 changed lines. The workflow below keeps that safe: a script handles the mechanical token replacement, and a byte-for-byte check confirms that no `<script>` block changed.

## What you're working with

| Concern | Where it lives today |
|---|---|
| App shell, top nav, **global styles** | `client/src/App.vue`. The `.top-nav` header holds the logo, `.nav-tabs` router-links, `<LanguageSwitcher />` and `<ProfileMenu />`, followed by `<FilterBar />` and `<main class="main-content">`. The unscoped `<style>` block defines the shared classes. |
| Routes | `client/src/main.js`: `/`, `/inventory`, `/orders`, `/spending`, `/demand`, `/restocking`, `/reports`. `Backlog.vue` exists but has no route; leave it unrouted. |
| Filters | `client/src/components/FilterBar.vue`: four selects plus a reset button. It is `position: sticky; top: 70px`, tied to the current 70px header height. |
| Views | `client/src/views/*.vue`, each with one `<style scoped>` block plus the shared global classes. Dashboard (about 1,270 lines) and Spending (about 850) are the largest. |
| Modals and dropdowns | `components/*Modal.vue` (fixed position, z-index 1000-2000), and the `.dropdown-menu` in `ProfileMenu.vue` / `LanguageSwitcher.vue`. |
| Text | `useI18n()` → `t('nav.*')` etc. in `client/src/locales/en.js` and `ja.js`. The "Reports" nav label is hard-coded in English. |

Shared global classes the views rely on:
- `.page-header`, `.stats-grid`
- `.stat-card` (with `.success/.warning/.danger/.info`), `.stat-label`, `.stat-value`
- `.card`, `.card-header`, `.card-title`
- `.table-container`, `table/th/td`
- `.badge` (with status, trend and priority variants)
- `.loading`, `.error`

Restyling these in one place does most of the work. Keep the class names, because every view's templates use them. Some views override them in their own scoped styles; Reports and Inventory redefine `.card`, `.stat-card`, `.badge`, `.loading` and `.error`. Delete those overrides so the global design wins.

Colour is spread around: about 425 hard-coded hex values in views and components, using the slate palette (`#0f172a` ink, `#64748b` muted, `#e2e8f0` borders, `#334155`/`#475569` secondary text), accents `#2563eb`/`#3b82f6`, and Tailwind-500 chart and status hues (`#10b981`, `#f59e0b`, `#ef4444`). The project's own rules (root `CLAUDE.md`) also apply: slate/gray palette, green/blue/yellow/red status colours, custom SVG charts, no emojis.

## Target design

### Layout shell (App.vue)

```
┌────────────┬──────────────────────────────────────────────┐
│ ▣ Catalyst │  Breadcrumb / page context        Lang  Avatar│  header: 64px, sticky top 0
│   Components├─────────────────────────────────────────────┤
│            │  Period [▾] Location [▾] Category [▾] ...  ⟳  │  FilterBar: sticky top 64px
│ OPERATIONS ├──────────────────────────────────────────────┤
│ ● Overview │                                              │
│   Inventory│   <router-view />                            │
│   Orders   │   content: max-width 1440px, padding 32px    │
│   Finance  │                                              │
│ PLANNING   │                                              │
│   Demand   │                                              │
│   Restock  │                                              │
│   Reports  │                                              │
└────────────┴──────────────────────────────────────────────┘
   240px fixed
```

- **Sidebar** (`<aside class="sidebar">`): fixed, 240px wide, full height, white surface with a right border.
  - **Brand at the top:** a small accent-coloured logo mark (an inline SVG box/cube icon in a rounded square), the company name, and the subtitle beneath it in muted `--text-xs`.
  - The subtitle ("Inventory Management System", which is longer in Japanese) doesn't fit on one line at 240px. Let it wrap to two lines rather than truncating it with an ellipsis.
  - **Nav:** render it from an array in `setup()` (`{ path, labelKey, icon }`, keyed by `path`), with one `router-link` per route. Each has a 20px inline SVG icon (stroke style, `currentColor`, about 1.75 stroke width) and its label.
  - **Groups:** **Operations** (Overview, Inventory, Orders, Finance) and **Planning** (Demand Forecast, Restocking, Reports), each with a small uppercase muted group label. "Analytics" is a poor name, because Restocking is an action rather than analysis.
  - **States:** active is an accent-soft background, accent text and a 3px accent bar on the left edge; hover is `--color-surface-muted`.
  - Use `router-link`'s `active-class` / `exact-active-class`, so that `/` is only active on an exact match, instead of the hand-written `$route.path ===` checks.
  - An optional muted footer at the bottom, such as a version label, is fine.
- **Header** (`<header class="app-header">`): sticky at `top: 0` inside the content column, 64px tall, white, bottom border.
  - Left: a breadcrumb (company name / current page name, derived from the nav array and `$route.path`), plus the hamburger button on narrow screens.
  - Right: `<LanguageSwitcher />` and `<ProfileMenu />`.
- **FilterBar goes in its own second sticky row,** directly under the header at `top: var(--header-height)`. Four selects with labels, plus the reset button, plus the header controls don't fit in one 64px row at a 1440px window (about 1,136px of content width), so don't try. Style its selects as the standard 36px inputs. Below 1024px it can wrap and stop being sticky.
- **Content**: `margin-left: var(--sidebar-width)`, inner wrapper `max-width: var(--content-max)`, padding `var(--space-8)`.
- **Responsive** (below 1024px): the sidebar becomes an off-canvas drawer that slides in from the left over a dimmed backdrop.
  - It opens from a hamburger button in the header, which has `aria-expanded` and an i18n `aria-label`.
  - It closes on a backdrop click, on Escape (a `keydown` listener added in `onMounted` and removed in `onUnmounted`), and on navigation (a `watch` on `route.path`).
  - The content then takes the full width.
  - Keep the open state in a `ref` in App.vue. These few lines of new `<script>` in App.vue are the one allowed script change.
  - No horizontal page scroll at 375px (see the overflow pitfall below).
- **i18n keys to add, in both `en.js` and `ja.js`:** `nav.reports` (replacing the hard-coded "Reports"), `nav.groupOperations`, `nav.groupPlanning`, `nav.toggleMenu` and `nav.mainNavigation` (for the `<nav aria-label>`).

### Design tokens

Define these once on `:root` in App.vue's global style block and use them everywhere. Consistent spacing comes from every margin, padding and gap coming from the same scale. `scripts/tokenize_styles.py` emits exactly these names, so define all of them before running it.

```css
:root {
  /* spacing: 4px base */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-10: 40px;

  /* surfaces and text */
  --color-bg: #f8fafc;  --color-surface: #ffffff;  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;  --color-text-secondary: #334155;
  --color-text-muted: #64748b;  --color-text-subtle: #94a3b8;

  /* accent and status: base / soft background / strong text (for badges) */
  --color-accent: #2563eb;   --color-accent-hover: #1d4ed8;  --color-accent-soft: #eff6ff;  --color-accent-strong: #1e40af;
  --color-success: #16a34a;  --color-success-soft: #f0fdf4;  --color-success-strong: #166534;
  --color-warning: #d97706;  --color-warning-soft: #fffbeb;  --color-warning-strong: #92400e;
  --color-danger: #dc2626;   --color-danger-soft: #fef2f2;   --color-danger-strong: #991b1b;
  --color-info: #0284c7;     --color-info-soft: #f0f9ff;     --color-info-strong: #075985;
  --color-neutral-soft: #f1f5f9;  --color-neutral-strong: #475569;

  /* charts keep their existing hues, so data colours don't shift meaning */
  --chart-blue: #3b82f6; --chart-green: #10b981; --chart-amber: #f59e0b;
  --chart-red: #ef4444;  --chart-slate: #64748b; --chart-violet: #8b5cf6;

  /* type */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --text-xs: 12px; --text-sm: 13px; --text-base: 14px; --text-md: 16px;
  --text-lg: 18px; --text-xl: 22px; --text-2xl: 28px;

  /* shape and depth */
  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.12);
  --focus-ring: 0 0 0 3px var(--color-accent-soft);

  /* layout and layering */
  --sidebar-width: 240px; --header-height: 64px; --content-max: 1440px;
  --z-filterbar: 45; --z-header: 50; --z-backdrop: 55; --z-sidebar: 60;
  --z-dropdown: 1000; --z-modal: 2000;
}
```

Values can be tuned, but keep the *structure*: a single spacing scale, semantic colour names with base/soft/strong variants, separate chart hues, and a small type scale. UI chrome (buttons, links, focus, active nav) uses `--color-accent`; data marks (bars, donut segments, legend dots) use `--chart-*`.

Inter is already first in the font stack. Don't add a webfont request or any new npm dependency. Icons are inline SVG.

### Shared component styling (global classes)

- **Page header**: title `--text-2xl`, weight 700, tight letter-spacing; description in `--text-base` muted text; `--space-6` below it. If a view has page-level actions, align them to the right of the title.
- **Section labels** (like the Dashboard's "Key performance indicators"): a small `--text-xs` uppercase muted label with letter-spacing is fine *here*, because it's tiny. Elsewhere use sentence case.
- **Stat cards**: surface background, 1px border, `--radius-lg`, `--shadow-sm`, padding `--space-5`.
  - The label is `--text-sm`, muted, sentence case.
  - The value is `--text-xl`/`--text-2xl` with weight 600 and `tabular-nums`, in `--color-text`.
  - The status variants show colour through a small accent, a dot or an icon chip next to the label, not a coloured value or a thick left border.
  - Any hover lift should be subtle.
- **Cards and card headers**: same surface, border, radius and shadow as stat cards. Cards set their padding through a variable, `.card { --card-pad: var(--space-6); padding: var(--card-pad) }`, so that a `.card-header` can run full-bleed with a bottom border:
  ```css
  .card-header { margin: calc(-1 * var(--card-pad)) calc(-1 * var(--card-pad)) var(--card-pad);
                 padding: var(--space-5) var(--card-pad); border-bottom: 1px solid var(--color-border); }
  ```
  `.card-title` is `--text-md`, weight 600. If a view sets its own card padding, change `--card-pad` rather than `padding`.
- **Tables**:
  - `th`: `--text-xs`, weight 600, muted, sentence case, on a `--color-surface-muted` background. Keep `th` sticky only where it already was.
  - `td`: `--text-base`, padding `--space-3 --space-4`, row borders in `--color-border`, hover `--color-surface-muted`.
  - Numeric columns: add a `class="num"` to their `th`/`td`, styled `text-align: right; font-variant-numeric: tabular-nums`.
- **Badges**: pill shape (`--radius-full`), `--text-xs`, weight 500, padding `2px var(--space-2)`, a `*-soft` background with `*-strong` text. Keep every variant name working (`success/warning/danger/info/increasing/decreasing/stable/high/medium/low`).
  - Some badge classes are built in `<script>` (`getStockBadge`, `getStockStatusClass`, `getFulfillmentClass` returning `'badge success'`, and similar). Grep for functions returning class strings and make sure each value they can return has a style.
- **Buttons and inputs** (filter selects, the Restocking slider and Place Order button, Create PO, modal buttons, the task form):
  - 36px tall, `--radius-md`, `--text-base`, weight 500.
  - Primary: accent fill with white text, hover `--color-accent-hover`. Secondary: white with a border.
  - Focus: `box-shadow: var(--focus-ring)` plus an accent border. Disabled at 50% opacity.
- **Modals**: `--radius-lg`, `--shadow-lg`, a backdrop of `rgba(15, 23, 42, 0.4)`, consistent header, body and footer padding (`--space-6`), z-index `var(--z-modal)`. TasksModal currently uses 1000; raise it.
- **Loading and error states**: centred, muted, `--space-10` padding; errors on a `--color-danger-soft` panel with `--color-danger-strong` text. No emojis.

## Workflow

1. **Baseline.**
   - Run `cd client && npx vite build` (it must pass).
   - Screenshot every route at 1440px (see "Verifying in a browser" below).
   - Note each view's visible pieces: stat cards, tables, charts, the modals it opens, the filters it reacts to.
   - Snapshot the `<script>` blocks so you can prove later that they didn't change. If `client/src` has no uncommitted changes, comparing against `git show HEAD:<file>` is enough. Otherwise copy `client/src` somewhere first.
2. **Shell and tokens first** (App.vue, FilterBar.vue, both locale files).
   - Build the sidebar, header, filter row, content area, drawer and `:root` tokens, and restyle the global classes.
   - This is the riskiest edit, so build and screenshot it before touching the views.
3. **Mechanical token pass.** Preview with `python3 .claude/skills/saas-redesign/scripts/tokenize_styles.py client/src --dry-run`, then run it without the flag.
   - It rewrites only `<style>` blocks in views and components, skipping App.vue and FilterBar.vue.
   - Hex values become tokens. Spacing snaps to the scale (off-scale values round to the nearest step). Font sizes and radii become tokens. White backgrounds become `--color-surface`.
   - It reports the hex values it couldn't map. Handle those by hand.
4. **Manual cleanup, view by view.** Do Dashboard, Spending, Inventory, Orders, Demand, Restocking and Reports, then the modal components:
   - Delete scoped rules that override the global classes (see "What you're working with").
   - Section spacing: `gap: var(--space-6)` between major blocks is a good default.
   - Replace thick coloured left-border accents and uppercase labels with the patterns above.
   - Add `class="num"` to numeric columns, and turn `style="cursor: pointer;"` into a `clickable-cell` class.
   - **Charts.** CSS variables work in CSS but **not** in SVG presentation attributes. `stroke="var(--chart-green)"` silently fails, and some Dashboard donut segments use `stroke="#10b981"` attributes.
     - Move those colours into classes, for example `.seg-delivered { stroke: var(--chart-green) }`. The same goes for inline `style` colours on legend dots.
     - Colours computed in `<script>` (such as `getChangeColor` in Demand, `cat.color` in Dashboard, and some in InventoryDetailModal) stay as they are, because script is off limits.
     - Don't change how charts compute geometry.
   - Edit only presentational `<template>` markup: classes, wrapper divs, a static `style` → class, or a `:style` colour → `:class` where the mapping is obvious. Never edit `<script>`, except the drawer state in App.vue.
   - **Delegation.** Root `CLAUDE.md` says significant `.vue` changes go through the `vue-expert` subagent. If that agent type is available, delegate the views in parallel batches, giving each batch the token block, the component styling rules and the chart note above. If it isn't available, do the work directly and say so in your summary.
5. **Verify.**
   - **Build:** `npx vite build` passes.
   - **Script integrity:** for every changed `.vue` file except App.vue, strip the `<style>` and `<template>` blocks and compare against the baseline. They must be byte-identical.
   - **Browser checks at 1440px and a true 375px:**
     - Exactly one sidebar item is active on each route, and `/` isn't active on other routes. The breadcrumb follows navigation.
     - The drawer opens from the hamburger and closes on backdrop, Escape and navigation.
     - Filters still change data. For example, setting Time Period to a month changes Dashboard revenue, and setting status to Delivered changes the Orders count.
     - The header and filter row stay stuck while scrolling.
     - The profile menu and the language switcher open, the language switches to JA, the sidebar labels translate without truncation, and nothing overflows.
     - The Tasks, inventory-detail and backlog-detail modals open above the sidebar and header. Use `document.elementFromPoint` over the sidebar to confirm the overlay is on top.
     - The Restocking slider updates the totals.
     - On every route, page width equals viewport width at 375px.
   - **Don't click Place Order** against the shared dev API unless the user is fine with creating a real (in-memory) order. Restarting the API clears it. Checking that the button renders and is enabled is enough.
   - Compare against the baseline screenshots. Nothing should be missing.
6. **Report**: list the files changed (`git diff --stat`), the token set, visual decisions the user might tweak (sidebar width, group names, accent colour, density, breadcrumb), anything you couldn't verify, and problems you noticed but deliberately left because they were there before. Don't commit unless asked. The repo is public.

## Verifying in a browser

Use a browser MCP (Playwright or Chrome DevTools) if one works. If it's missing, or fails with "browser is already running" because its profile is locked, use the bundled driver:

```bash
OUT_DIR=/tmp/redesign-shots node .claude/skills/saas-redesign/scripts/browser.mjs ./steps.mjs
```

`steps.mjs` default-exports `async (page) => { ... }`. The page object offers:
- `size(w, h)`, `go(url)`, `eval(js)`
- `click(sel)` and `mousedown(sel)`
- `key('Escape')`, `overflow()`, `shot(name)`
- console errors are collected automatically

Read the PNGs with the Read tool. The comment at the top of the script has a worked example.

Two traps:
- Plain `chrome --headless --window-size=375,...` silently renders about 500px wide, because headless clamps the minimum window width. Use `page.size(375, 800)`, which emulates a true viewport.
- ProfileMenu and LanguageSwitcher items react to `@mousedown`, not `click`. Use `page.mousedown()` for them.

Console noise that was there before the redesign: a 404 from `GET /api/tasks` (App.vue loads tasks from an endpoint the server doesn't have) and "Failed to resolve component: PurchaseOrderModal" on the Dashboard. Don't chase these.

## Pitfalls seen in this codebase

- **Horizontal overflow at 375px** comes from fixed-width layouts, not from the sidebar. Check `page.overflow()` on every route. Known offenders:
  - grids using `minmax(450px, 1fr)`
  - the two-column grid in Spending
  - the Dashboard charts grid
  - wide bar or label rows in the Spending and Reports charts
  Use `minmax(min(100%, 450px), 1fr)`, or let wide charts scroll inside their card with `overflow-x: auto`.
- **Don't leave the 70px assumption in place.** FilterBar's sticky offset was tied to the old header height; use `top: var(--header-height)`.
- **Leave `#app` / `.app` sizing intact.** Modals are `position: fixed`, so a parent with `transform`, `filter` or `overflow: hidden` breaks them. Don't put those on ancestors of the modals, and keep the drawer's `transform` on the sidebar itself.
- **i18n.** Every new visible string needs a key in both locale files. Japanese labels are longer, so let brand text wrap and use `text-overflow: ellipsis` only as a last resort on nav labels.
- **Use unique `:key`s.** Key the nav array by `path`, never by index (a project rule).
- **Leave existing bugs alone.** Unrelated problems you notice, such as hard-coded English strings in Reports and Dashboard actions, belong in the report, not in this diff.
