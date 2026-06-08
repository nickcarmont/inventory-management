---
name: saas-ui-redesign
description: Redesign the Vue 3 frontend into a modern SaaS-style interface with a left vertical navigation sidebar, consistent spacing, and a polished professional look. Use this skill when asked to redesign the UI, modernize the layout, add a sidebar navigation, or make the app look like a SaaS product.
---

# SaaS UI Redesign

Transform the app shell from its top-nav-bar layout into a modern SaaS layout: a fixed vertical sidebar on the left for navigation, a slim top bar for global controls, and a consistent, polished content area.

## Mandatory Rules (from CLAUDE.md)

1. **Delegate all `.vue` file creation/modification to the `vue-expert` subagent** via the Task tool. This skill defines *what* to build; vue-expert does the editing. Pass the relevant sections of this skill in the subagent prompt.
2. **Verify with Playwright MCP tools** (`mcp__playwright__*`) against `http://localhost:3000`. Take screenshots before and after.
3. **No emojis in the UI.** Use inline SVG icons (16–20px, `stroke="currentColor"`, stroke-width 1.5–2, Lucide/Feather style).
4. Keep the slate/gray design system (#0f172a, #64748b, #e2e8f0) and existing status colors.

## Current Architecture (do not break)

- `client/src/App.vue` — owns the app shell **and all global (non-scoped) styles** used by every view: `.page-header`, `.stats-grid`, `.stat-card`, `.card`, `.card-header`, `.card-title`, `.table-container`, `table/th/td`, `.badge.*`, `.loading`, `.error`. Views depend on these classes; restyle them, never remove or rename them.
- Top nav currently contains: logo + subtitle, 6 `router-link` tabs (Overview, Inventory, Orders, Finance, Demand Forecast, Reports), `<LanguageSwitcher />`, `<ProfileMenu />` (which opens `ProfileDetailsModal` and `TasksModal`).
- `<FilterBar />` renders below the nav and must remain globally visible.
- Nav labels come from `t('nav.*')` via `useI18n` — keep every `t()` call and `router-link` `to` path exactly as-is (Reports is hardcoded text; leave it unless adding locales).
- Views in `client/src/views/*.vue`: Dashboard, Inventory, Orders, Spending, Demand, Backlog, Reports.

## Target Layout

```
┌────────────┬──────────────────────────────────────┐
│  Sidebar   │  Top bar (FilterBar · Lang · Profile)│
│  (fixed,   ├──────────────────────────────────────┤
│   240px)   │                                      │
│            │  Main content (scrolls)              │
│  Logo      │  max-width 1400px, padding 2rem      │
│  ──────    │                                      │
│  Nav links │                                      │
│  ──────    │                                      │
│  (footer:  │                                      │
│   version/ │                                      │
│   user)    │                                      │
└────────────┴──────────────────────────────────────┘
```

### App shell (App.vue template)

```html
<div class="app">
  <aside class="sidebar"> ... logo, nav, sidebar-footer ... </aside>
  <div class="app-body">
    <header class="top-bar"> <FilterBar /> <LanguageSwitcher /> <ProfileMenu /> </header>
    <main class="main-content"> <router-view /> </main>
  </div>
</div>
```

- `.app` — `display: flex; min-height: 100vh;`
- `.sidebar` — `position: fixed; top: 0; left: 0; bottom: 0; width: 240px;` dark slate background `#0f172a`, `z-index: 100`.
- `.app-body` — `margin-left: 240px; flex: 1; display: flex; flex-direction: column; min-width: 0;`
- `.top-bar` — white, `border-bottom: 1px solid var(--border)`, sticky `top: 0`, `z-index: 90`, height ~64px, FilterBar on the left, LanguageSwitcher + ProfileMenu pushed right with `margin-left: auto`. If FilterBar is too wide for one row, keep it as a second row inside the sticky top-bar rather than truncating filters.
- `.main-content` — `flex: 1; max-width: 1400px; width: 100%; padding: 2rem;`
- Modals (`ProfileDetailsModal`, `TasksModal`) stay mounted at the `.app` root; verify their overlay `z-index` exceeds the sidebar's (raise to 1000+ if needed).

### Sidebar design

- **Dark sidebar** on `#0f172a`, white logo text, subtitle in `#94a3b8`.
- Nav links: vertical stack, `0.625rem 0.75rem` padding, `border-radius: 8px`, `margin: 0 0.75rem`, gap `2px`. Color `#94a3b8`; hover → `#e2e8f0` text on `rgba(255,255,255,0.06)`; active → white text on `rgba(255,255,255,0.1)` with a 3px accent bar (`#3b82f6`) on the left edge or `border-left`.
- Each link: icon + label, `display: flex; align-items: center; gap: 0.75rem;`.
- Keep the same 6 routes and active-route logic (`$route.path` match).
- Optional section label above links (e.g. "MENU") — `0.688rem`, uppercase, `letter-spacing: 0.08em`, `#64748b`.
- Sidebar footer pinned to bottom: thin top border `rgba(255,255,255,0.08)`, app version or workspace name in `#64748b`.

### Design tokens

Define once in App.vue global styles and use throughout:

```css
:root {
  --sidebar-bg: #0f172a;
  --sidebar-width: 240px;
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-secondary: #64748b;
  --accent: #3b82f6;
  --radius: 10px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
  --space-1: 0.5rem; --space-2: 0.75rem; --space-3: 1rem;
  --space-4: 1.5rem; --space-5: 2rem;
}
```

### Spacing & polish rules

- One spacing scale everywhere: 0.5 / 0.75 / 1 / 1.5 / 2rem. No ad-hoc values like 1.3rem or 22px.
- Cards: `--surface` background, `1px solid var(--border)`, `border-radius: var(--radius)`, `padding: var(--space-4)`, `box-shadow: var(--shadow-sm)`; hover lifts to `--shadow-md`.
- Consistent vertical rhythm: `page-header` → `stats-grid` → cards all separated by `var(--space-4)`.
- Tables: keep current style; ensure first/last cell padding aligns with card padding.
- Transitions: `0.15s–0.2s ease` only on `background-color`, `color`, `border-color`, `box-shadow`. No layout-property animations.
- Typography stays Inter; page titles `1.5rem/700`, card titles `1rem/600`, body `0.875rem`.

### Responsive

- `max-width: 1024px`: collapse sidebar to icon-only 64px (hide labels, center icons, show `title` tooltips); `app-body` margin-left matches.
- `max-width: 768px`: FilterBar controls wrap; top-bar may grow in height.

## Process

1. **Baseline**: start servers if needed (`/start` skill or `cd client && npm run dev`), screenshot `http://localhost:3000` with Playwright.
2. **Shell redesign**: Task → vue-expert to restructure `App.vue` per "App shell" + "Sidebar design" + "Design tokens" above. This is the bulk of the work — most view styling comes from App.vue globals.
3. **Top bar**: same vue-expert task — move FilterBar, LanguageSwitcher, ProfileMenu into `.top-bar`; check `FilterBar.vue` for styles assuming full-width placement (own background/borders) and flatten them so it sits inline in the top bar.
4. **View consistency pass**: Task → vue-expert to sweep `client/src/views/*.vue` for scoped styles that conflict with the tokens (hardcoded paddings, off-scale margins, duplicate card styles) and align them. Do not change any business logic, computed properties, or API calls.
5. **Verify with Playwright** on all 7 routes (`/`, `/inventory`, `/orders`, `/spending`, `/demand`, `/backlog`, `/reports`):
   - Sidebar visible and fixed while content scrolls; active link highlights correctly per route.
   - Filters still work (change warehouse/category, confirm data updates).
   - ProfileMenu opens; both modals render above the sidebar.
   - LanguageSwitcher still swaps nav labels.
   - No horizontal scrollbar at 1440px and 1280px widths; check 1024px collapsed state.
   - Screenshot each route; check browser console for errors.
6. **Review**: Task → code-reviewer on the changed files.

## Pitfalls

- Removing or renaming a global class from App.vue silently breaks every view — restyle in place.
- `FilterBar` sticky/positioning styles may fight the new sticky top-bar; the top-bar owns stickiness, FilterBar becomes a plain flex child.
- `ProfileMenu` dropdown likely positions relative to the old top-right nav; re-test its placement in the new top bar.
- Sidebar `position: fixed` + content `margin-left` (not flex-only) so the sidebar never scrolls away.
- Keep `v-for` keys unique (`sku`, `month` — never `index`) in any touched template.
