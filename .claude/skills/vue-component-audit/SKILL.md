---
name: vue-component-audit
description: Audit the Vue 3 components in client/src (views, components, App.vue) and produce a ranked report of optimizations for rendering performance, code reuse, component size/structure, and leftover debug code, with file:line evidence and a concrete suggested fix for each. Report only; it never edits code. Use this skill whenever the user asks to analyze, audit, review or health-check the Vue frontend or a specific .vue file, asks why the UI is slow or re-renders too much, wants to find duplicated logic or candidates for composables/shared components, asks which components are too big or should be split, or wants to clean up console.log noise, even if they don't say "audit".
---

# Vue component audit

Produce a prioritized, evidence-backed report of how the Vue 3 client could be faster and less repetitive. The value of this report is that every item is **real, located, and actionable**: a reader should be able to open `file:line`, see the problem, and know what to change. A long list of generic advice ("consider using computed") is worth less than five verified findings.

This skill is **report-only**. Don't edit `.vue` files. If the user then asks for fixes, root `CLAUDE.md` requires delegating significant `.vue` changes to the `vue-expert` subagent; hand it the relevant findings.

## Scope

Default to everything under `client/src` (`views/`, `components/`, `App.vue`, plus `composables/` and `utils/` as reuse targets). If the user names a file or area, audit only that, but still check the shared `composables/` and `utils/` so reuse suggestions point at what already exists.

Read `client/CLAUDE.md` first if it isn't already in context. It sets this project's conventions (Composition API with `setup()`, unique `v-for` keys, computed for derived data, extraction thresholds), and findings should be judged against those, not against generic taste.

## Workflow

### 1. Run the pre-scan

```bash
python3 .claude/skills/vue-component-audit/scripts/scan_vue.py client/src
```

(Pass a single file or directory instead to narrow the scope; add `--json` for structured output.)

It reports **candidates**, not verdicts:

| Kind | Meaning |
|---|---|
| `render-call-iterates` | A function called from the template whose body loops over component data. It reruns on every render; usually belongs in a `computed`. |
| `vfor-index-key` / `vfor-no-key` | `v-for` keyed by loop index, or with no key. |
| `unresolved-component` | A PascalCase tag used in the template that the script never imports. At runtime Vue renders nothing and warns. |
| `console` | `console.log/debug/info/warn/trace` left in a component (`console.error` in a catch is fine and not reported). |
| `deep-watch` | A `deep: true` watcher. Fine on small objects, costly on large arrays. |
| `large-file` / `large-template` | Over 400 file lines / 200 template lines. |
| Cheap render-time calls | Formatter-style helpers called in the template. Listed for context only, as these are normally fine. |
| Helper names in more than one component | Same function name defined in several files: the main lead for reuse. |

### 2. Verify each candidate by reading the code

The scanner is regex-based and cannot understand intent, so open each location before reporting it. Typical things to confirm or reject:

- **Render-time calls**: Is the call inside a `v-for`? Then its cost multiplies by the row count (e.g. a helper that scans the whole list to find a max, called once per bar, is O(n²) per render). Is the same call made several times with the same argument (e.g. one per status card)? A single `computed` that groups the data once replaces all of them.
- **Index keys**: Is the list ever reordered, filtered or spliced? If it's static and append-only the impact is low; say so. Find the natural unique field (`sku`, `month`, `quarter`, `id`) to recommend.
- **Duplicate helper names**: Diff the bodies. Same name doesn't mean same logic (two `close()` methods that each emit `'close'` are trivial and not worth extracting; six `formatDate()`s with three different output formats are a real inconsistency). Check whether `utils/` or `composables/` already provides it: e.g. `utils/currency.js` exports `formatCurrency`, so a local `formatMoney` should reuse that rather than becoming yet another helper.
- **Large files**: Look at what the bulk is. A 1,100-line file that is 700 lines of scoped CSS is a different problem from 700 lines of logic. Name the concrete sub-components or composables you'd extract (each self-contained card, chart or table is a natural seam).

### 3. Look for what the scanner can't see

Spend some judgment on patterns that need reading, especially in the largest views:

- **Duplicated markup**: The same card, stat tile, badge, table shell or modal frame repeated across views (compare the templates of the detail modals side by side). Suggest a shared component with the props it would need.
- **Duplicated data-loading**: Several views with the same `loading`/`error`/`try`/`finally` + filter `watch` pattern can share a composable (e.g. `useAsyncData(fetcher, deps)`).
- **Formatting bugs from duplication**: Copies drifting apart produce visible bugs (e.g. a template adding `+` to a value whose formatter already adds `+`). Report them; they're strong evidence that the logic should live in one place.
- **Reactivity hazards**: Derived data stored in `ref`s and recomputed manually instead of `computed`; props mutated directly; destructured props losing reactivity; watchers that refetch on every keystroke without debounce.
- **API consistency**: Components still on the Options API (`data()`/`methods`) when the project standard is Composition API. Mention it once as a structural note, not once per file.

Skip things that cost more to change than they return. A finding needs a real benefit: faster renders on realistic data, removal of genuine duplication, or a visible bug.

### 4. Write the report

Rank by impact (user-visible bugs and per-render waste on lists first, cosmetic cleanups last). Use this structure:

```markdown
# Vue component audit: <scope>

## Summary
<2-4 sentences: overall health, the top 3 things worth doing, rough effort.>

## Findings

### 1. <Short title naming the problem> [Performance | Reuse | Structure | Debug code] · <High | Medium | Low>
**Where:** `client/src/views/Orders.vue:14`, `:18`, `:22`, `:26`
**What:** <What the code does now, quoted or paraphrased tightly.>
**Why it matters:** <Concrete cost: reruns N times per render, O(n²) per chart draw, 6 diverging copies, renders nothing, etc.>
**Suggested fix:** <Specific change, with a short code sketch when it helps.>

### 2. ...

## Reuse opportunities
<Table: proposed shared piece | where it's duplicated today | target location (composables/, utils/, components/)>

## Not worth changing
<Brief list of scanner hits you checked and rejected, with the reason, so the reader knows they were considered.>
```

Severity guide: **High**: user-visible bug, or work that scales with data size on every render. **Medium**: real duplication (3+ copies) or a file that blocks safe changes. **Low**: debug noise, minor inconsistencies.

Keep code sketches short and in the project's style (Composition API, `computed`, `.value` in script). Write the report to the conversation; save it to a file only if the user asks.
