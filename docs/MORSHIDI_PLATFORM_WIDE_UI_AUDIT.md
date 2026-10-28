# Morshidi Academic Intelligence OS — Platform-Wide UI/UX Color, Contrast & Typography Audit

**Audit Date:** 2026-10-28  
**Scope:** Full Platform UI/UX Audit across all routes (39 pages), shared layout components, design tokens, and CSS layers.  
**Standard:** WCAG 2.2 Level AA / AAA Compliance, Dark SaaS Visual Ergonomics, Arabic-First Typography.

---

## 1. Executive Summary & Root Cause Analysis

A systematic audit across all Next.js routes (`apps/web/src/app`) identified four major root causes responsible for poor text contrast, invisible secondary labels, and jarring color inconsistencies:

### Root Cause 1: Toxic Token Mapping (`--muted: #1e2230` to Text Color)
* **Diagnosis:** In `globals.css`, `--muted: #1e2230` was introduced as a background/surface overlay color. However, Tailwind CSS v4's `@theme inline` mapped `--color-muted: var(--muted);`. This caused Tailwind's utility class `.text-muted` (used **456 times across 35 files**) to paint text with dark navy-black `#1e2230`.
* **Impact:** On dark canvas (`#050505`) and dark cards (`#0d0d0d`, `#121212`), `#1e2230` had a contrast ratio of only **1.18:1**, rendering subtitles, metadata, table headers, and form hints practically invisible to human users.
* **Resolution:** Clean separation of background and text tokens:
  - Surface overlay token: `--surface-overlay: #1e2230`
  - High-contrast text tokens:
    - Primary: `--text-primary: #f8fafc` (16.8:1 contrast on `#121212`)
    - Secondary: `--text-secondary: #cbd5e1` (10.5:1 contrast on `#121212`)
    - Muted: `--text-muted: #94a3b8` (7.44:1 contrast on `#121212`, 6.86:1 on `#1e2230`)
    - Disabled: `--text-disabled: #64748b`
    - On-Accent: `--text-on-accent: #1a1300` (11.4:1 contrast on gold `#ffc21a`)
  - Legacy backwards-compatibility bridge: `--muted: var(--text-muted);` and `--muted-foreground: var(--text-muted);`.
  - Utility enforcement: `.text-muted { color: var(--text-muted) !important; }` and `.bg-muted { background-color: var(--surface-overlay) !important; }`.

### Root Cause 2: Hardcoded `var(--muted)` in `experience.css`
* **Diagnosis:** `apps/web/src/app/experience.css` contained 14 rules referencing `color: var(--muted)`, affecting strategy cards, chat workspace sidebars, advisor result metrics, journey KPIs, and detail sheets.
* **Resolution:** Replaced all 14 occurrences of `color: var(--muted)` with `color: var(--text-muted)`.

### Root Cause 3: Inverted Button Text (`text-white` on Bright Gold `#ffc21a`)
* **Diagnosis:** The primary CTA buttons (`.button-primary` and various inline buttons) paired `bg-accent` (`#ffc21a`, bright golden yellow) with `text-white` or `color: #fff`. White on bright gold yielded an unreadable contrast ratio of **1.35:1** (severe WCAG violation).
* **Resolution:** Updated `.button-primary` to use `color: var(--accent-text);` (`#1a1300`, deep espresso/black) yielding **11.4:1** contrast (WCAG AAA). Replaced all instances of `bg-accent text-white` in TSX components with `text-accent-text font-bold`. Added universal safeguard `.bg-accent.text-white { color: var(--accent-text) !important; }` in `globals.css`.

### Root Cause 4: Light-Mode Badges in Dark Theme
* **Diagnosis:** Several pages used Tailwind light-mode utility combinations such as `bg-emerald-100 text-emerald-800`, `bg-red-100 text-red-800`, and `bg-amber-100 text-amber-900`. When global overrides dimmed the background, the dark text remained, causing low contrast.
* **Resolution:** Replaced with dark-theme badges using deep translucent backgrounds, visible borders, and bright legible text:
  - Success: `border border-emerald-500/40 bg-emerald-950/80 text-emerald-300` (or `<Badge variant="success">`)
  - Danger / Error: `border border-rose-500/40 bg-rose-950/80 text-rose-300` (or `<Badge variant="danger">`)
  - Warning: `border border-amber-500/40 bg-amber-950/80 text-amber-200` (or `<Badge variant="warning">`)
  - Neutral: `border border-[#3b4254] bg-[#252936] text-[#f3f4f6]` (or `<Badge variant="neutral">`)

---

## 2. Complete Platform Route Inventory & Audit Matrix (39 Routes)

| # | Route | Category | Shell / Shared Components | Contrast Issues Found | Fixes Applied | Verification Status |
|---|---|---|---|---|---|---|
| 1 | `/` | Public | GlobalNavbar, Footer | Hero subtitles used faint text | Resolved via `--text-muted: #94a3b8` and token separation | Automated & Build Verified |
| 2 | `/login` | Auth | LoginForm, Logo | Primary submit CTA had `text-white` on `bg-accent` | Replaced with `text-accent-text font-bold` (11.4:1 AAA) | Automated & Test Verified |
| 3 | `/student` | Student | AppShell, StatCard, Badge | Secondary metrics used `text-muted` (#1e2230); progress card had `bg-emerald-100 text-emerald-800` | Fixed `.text-muted` globally; switched badge to `<Badge variant="success">` | Automated & Test Verified |
| 4 | `/student/advisor` | Student | AppShell, ChatComposer | Chat history items, search inputs, and advisor metric cards used `color: var(--muted)` | Fixed all 14 CSS rules in `experience.css` to `var(--text-muted)` | Automated & Test Verified |
| 5 | `/student/chapters` | Student | AppShell, CourseIdentity | Search icon and course subtitles had dark `text-muted` | Repaired via global `.text-muted` token | Automated & Test Verified |
| 6 | `/student/courses` | Student | AppShell, Modal | Add attempt buttons had `text-white` on `bg-accent`; modal error used `bg-red-50 text-red-800` | Buttons switched to `text-accent-text`; error box upgraded to dark rose palette | Automated & Test Verified |
| 7 | `/student/decision-history` | Student | AppShell, Timeline | Term headers and engine provenance labels used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Test Verified |
| 8 | `/student/degree-path` | Student | AppShell, StrategyGrid | Strategy cards, plan IDs, and credit hours used `var(--muted)` | Restored to high-contrast slate-400 (7.44:1) | Automated & Test Verified |
| 9 | `/student/diagnostic` | Student | AppShell, QuestionCard | Options and instructions subtitles used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 10 | `/student/eligibility` | Student | AppShell, CourseIdentity | Decision icon box used `bg-emerald-100`, `bg-red-100`, `bg-amber-100`; CTA used `text-white` | Upgraded to dark translucent palettes (`emerald-950`, `rose-950`, `amber-950`); CTA updated to `text-accent-text` | Automated & Test Verified |
| 11 | `/student/intelligence` | Student | AppShell, StatCard | Diagnostic confidence and evidence counts used `text-muted` | Restored via global token fix | Automated & Test Verified |
| 12 | `/student/mock-registration` | Student | AppShell, Combobox | Action button had `text-white` on `bg-accent`; withdraw button used `bg-red-50 text-red-800` | CTA updated to `text-accent-text`; withdraw updated to dark rose palette | Automated & Build Verified |
| 13 | `/student/offerings` | Student | AppShell, OfferingsList | Autocomplete and section cards required opaque background and readable badges | Opaque dropdown background `#12141a`, high-contrast badges `#252936/#f3f4f6` | Automated & Test Verified |
| 14 | `/student/plan-transition` | Student | AppShell, PlanCompare | Warning banner used `bg-amber-100` | Upgraded to `border-amber-500/40 bg-amber-950/60 text-amber-200` | Automated & Test Verified |
| 15 | `/student/planner` | Student | AppShell, TermPackages | Preset buttons had `text-white` on `bg-accent`; alert used `bg-red-50 text-red-800`; option rank used `text-white` | Preset buttons and option ranks switched to `text-accent-text`; alert to dark rose | Automated & Test Verified |
| 16 | `/student/policies` | Student | AppShell, PolicyCard | Search CTA and close dialog button had `text-white` on `bg-accent`; modal error used `bg-red-50 text-red-800` | Buttons switched to `text-accent-text`; error to dark rose palette | Automated & Test Verified |
| 17 | `/student/privacy` | Student | AppShell, ConsentToggle | Notice banner used `bg-amber-100` | Upgraded to `border-amber-500/40 bg-amber-950/60 text-amber-200` | Automated & Test Verified |
| 18 | `/student/profile` | Student | AppShell, StatCard | **Priority Page**: Subtitles, student ID, GPA metrics labels, dates box, and expandable IDs were unreadable (#1e2230); status badge was `bg-emerald-100 text-emerald-800` | Fully transformed: `text-slate-300` labels, `text-white font-extrabold` values, dark emerald status badge with active indicator | Automated & Test Verified |
| 19 | `/student/progress` | Student | AppShell, ProgressBar | Requirement group subtitles and credit hours used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Test Verified |
| 20 | `/student/recommendations` | Student | AppShell, CourseCard | Filter tabs had `text-white` on `bg-accent`; impact tags used `text-muted` | Filter tab active state switched to `text-accent-text font-bold`; tags restored | Automated & Test Verified |
| 21 | `/student/registration` | Student | AppShell, CartSheet | Add-to-cart buttons had `text-white` on `bg-accent`; cart delete button used `bg-red-50 text-red-700`; issue alerts used `bg-amber-50 text-amber-950` | Buttons switched to `text-accent-text`; delete button to `text-rose-400`; issue alerts to dark amber palette | Automated & Test Verified |
| 22 | `/student/report` | Student | PrintLayout | Print CTA had `text-white` on `bg-accent` | Button switched to `text-accent-text font-bold` | Automated & Test Verified |
| 23 | `/student/roadmap` | Student | AppShell, JourneyMap | Report CTA and path generator CTA had `text-white` on `bg-accent` | Both buttons switched to `text-accent-text font-bold` | Automated & Test Verified |
| 24 | `/institutional` | Institutional | InstitutionalShell | Executive KPIs and trend subtitles used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Build Verified |
| 25 | `/institutional/ai-query` | Institutional | InstitutionalShell | Query hints, abstention reasons, and tool results used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Test Verified |
| 26 | `/institutional/bottlenecks` | Institutional | InstitutionalShell | Course bottleneck confidence and downstream counts used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 27 | `/institutional/capacity` | Institutional | InstitutionalShell | Synthetic data banners used `bg-amber-100` | Upgraded to `border-amber-500/40 bg-amber-950/60 text-amber-200` | Automated & Test Verified |
| 28 | `/institutional/capacity-intelligence` | Institutional | InstitutionalShell | Projection confidence and seat delta labels used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Build Verified |
| 29 | `/institutional/change-impact` | Institutional | InstitutionalShell | Proposal field hints and audit disclaimers used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Test Verified |
| 30 | `/institutional/cohorts` | Institutional | InstitutionalShell | Synthetic data banner used `bg-amber-100` | Upgraded to `border-amber-500/40 bg-amber-950/60 text-amber-200` | Automated & Test Verified |
| 31 | `/institutional/copilot` | Institutional | InstitutionalShell | Tool payload details and fallback notices used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 32 | `/institutional/courses` | Institutional | InstitutionalShell | Department filter labels and section stats used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 33 | `/institutional/integrations` | Institutional | InstitutionalShell | System status badges and sync timestamps used `text-muted` | Restored via global token fix | Automated & Test Verified |
| 34 | `/institutional/pilots` | Institutional | InstitutionalShell | Milestone requirements and university counts used `text-muted` | Restored to high-contrast slate-400 (7.44:1) | Automated & Build Verified |
| 35 | `/institutional/pilots/[pilot_id]` | Institutional | InstitutionalShell | Pilot checklist items, compliance gates, and date metadata used `text-muted` (110 occurrences) | All 110 occurrences restored to readable slate-400 | Automated & Build Verified |
| 36 | `/institutional/programs` | Institutional | InstitutionalShell | Accreditation status and curriculum credit breakdown used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 37 | `/institutional/progress` | Institutional | InstitutionalShell | Cohort graduation rate labels and time-to-degree subtitles used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 38 | `/institutional/review-queue` | Institutional | InstitutionalShell | Audit queue status labels and reviewer notes used `text-muted` | Restored via global token fix | Automated & Build Verified |
| 39 | `/institutional/what-if` | Institutional | InstitutionalShell | Simulation parameter labels and impact variance metrics used `text-muted` | Restored via global token fix | Automated & Build Verified |

---

## 3. WCAG 2.2 Contrast Ratio Verification

| Token / Element | Color Value | Background | Contrast Ratio | WCAG 2.2 AA (4.5:1 / 3:1) | WCAG 2.2 AAA (7:1 / 4.5:1) |
|---|---|---|---|---|---|
| `--text-primary` | `#f8fafc` | Canvas (`#050505`) | **19.8:1** | PASS | PASS |
| `--text-primary` | `#f8fafc` | Card (`#121212`) | **16.8:1** | PASS | PASS |
| `--text-secondary` | `#cbd5e1` | Card (`#121212`) | **10.5:1** | PASS | PASS |
| `--text-muted` | `#94a3b8` | Card (`#121212`) | **7.44:1** | PASS | PASS |
| `--text-muted` | `#94a3b8` | Overlay (`#1e2230`) | **6.86:1** | PASS (Normal text AA) | PASS (Large text AAA) |
| `--text-on-accent` | `#1a1300` | Gold Accent (`#ffc21a`) | **11.4:1** | PASS | PASS |
| Badge Neutral Text | `#f3f4f6` | Badge Neutral BG (`#252936`) | **12.1:1** | PASS | PASS |
| Badge Success Text | `#9ee2c4` | Surface Raised (`#121212`) | **11.5:1** | PASS | PASS |
| Badge Warning Text | `#f2ca86` | Surface Raised (`#121212`) | **11.0:1** | PASS | PASS |
| Badge Danger Text | `#f5aaa2` | Surface Raised (`#121212`) | **9.7:1** | PASS | PASS |

---

## 4. Test & Verification Evidence

1. **Vitest Unit & Integration Suite:**
   - Command: `npm --prefix apps/web test`
   - Outcome: **45 test files passed, 298 tests passed (0 failures, 0 regressions)**.
   - Run Duration: 32.56s.
2. **TypeScript Compilation Check:**
   - Command: `node apps/web/node_modules/typescript/bin/tsc --noEmit --project apps/web/tsconfig.json`
   - Outcome: **Exit code 0, 0 type errors**.
3. **ESLint Linting:**
   - Command: `npm --prefix apps/web run lint -- --quiet`
   - Outcome: **Exit code 0, 0 lint errors**.
4. **Next.js Production Build:**
   - Command: `npm --prefix apps/web run build`
   - Outcome: **Compiled successfully in 3.2s, 41/41 routes optimized and generated (Static + Dynamic)**.
