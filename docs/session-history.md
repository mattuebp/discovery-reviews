<!--
  Read this FIRST when picking up work on this project - a new machine, a
  new Claude Code conversation, or just after time away. It's the narrative
  companion to `git log`: not just what changed, but why, and what's still
  mid-flight.

  Convention: newest entry on top. Add a new entry every time you commit -
  see CLAUDE.md's Conventions section for the standing instruction. Each
  entry is a few sentences per commit, in plain language, capturing
  decisions and reasoning that a diff alone won't show.
-->

# Session History

## In progress — not yet committed (as of 2026-08-20)

**The Product Opportunity Report is finally a real Skill** - the piece
explicitly deferred since the pattern was first drafted (see the `a8322c`
entry below): "doc/skill work comes after the pattern is proven in tested
code." That happened in `75f11ee`; this session closes the loop.

What happened:
- Matheus collected a fresh, larger batch via the (now-fixed)
  per-rating web app: 150 reviews, 1-3 star only. Hand-labeled all 150
  through this conversation (144 got usable themes; 6 were too short/
  generic). Saved to `scripts/output/labels.json` - already matching the
  `reviews_raw.json` the web app writes server-side, so no file-juggling
  needed even though Matheus downloaded a copy to his Desktop first.
- Recomputed the report using the real `motor/pipeline/report.py`
  functions this time (not a scratchpad script) and republished the same
  Hevy artifact URL with the bigger batch. Important honesty catch: a
  1-3-star-only sample structurally produces **zero Strength themes** -
  made that explicit right next to the sentiment chart and as its own
  empty-state box, instead of letting an empty section look like a
  finding.
- Matheus then asked for the report-building pattern itself to become a
  real Skill (`.claude/skills/`), with a new instruction: split
  opportunities into **Kind 1 (In-Product)** - bugs, pricing, sync, scoped
  to the analyzed app's own backlog - versus **Kind 2 (New-Venture)** -
  gaps that could become Matheus's own separate MVP, independent of the
  analyzed app's roadmap. Wrote `.claude/skills/product-opportunity-report/SKILL.md`:
  reuses the tested `assemble_report()`/`classify_theme()` pipeline for
  Pain/Strength/Mixed, but treats the Kind 1/Kind 2 split as an explicit
  judgment call made while drafting (a "would this stand alone as its own
  pitch?" test), not something computed in `motor/` - it doesn't reduce to
  a count or percentage the way Pain/Strength does.
- The Skill hasn't been run yet on the current 150-review batch - the
  published artifact still uses the old undifferentiated backlog/appendix
  structure. Next session (or later this one) should re-run it with the
  new Kind 1/Kind 2 split and republish.

`docs/how-to-test.md` does not yet mention the Skill for non-technical
readers - still pending, lower priority than getting the split itself
right first.

---

## Commit log

### `d88b053` — Fix rating filters being starved by recency bias (2026-08-09)
Matheus filtered to 1-3 star reviews with sample size 500 and got only 14
back. Root cause, walked through with him live: `collect()` fetched one
pool of the 300 newest reviews of any rating, filtered afterward - an app
whose recent reviews skew positive (Hevy's newest 300 were 256 five-star)
starves a low-star filter down to almost nothing that way. Investigated
before fixing: confirmed live that Google Play supports server-side
exact-rating filtering (`filter_score_with`) - 100 requested one-star
reviews returned 100 genuine ones spanning 7 months, not a handful. Built
`GooglePlaySource.collect_by_ratings()`: each selected rating now fetched
as its own targeted pool; with no filter, the single mixed pool stays
(the natural rating proportion is real signal). Full TDD cycle, 6 new
tests. Wired into both `webapp/app.py` and `scripts/1_collect_and_export.py`.
Re-ran the exact scenario that surfaced the bug: 14 -> 500, confirmed
genuinely all 1-3 star, no leakage. `CLAUDE.md`'s "Bounded pool"
architecture bullet rewritten to match the new behavior.

### `a8edeb8` — Add app search interface, fix a real google-play-scraper bug, add rule 6 (2026-08-09)
Built `webapp/` - the project's first running interface (a small local
Flask app), chosen over a terminal-picker alternative after Matheus
reviewed the trade-off. Along the way, investigated and fixed a real bug
in `google_play_scraper.search()`: it loses the app id specifically for
Google's "exact match" top result card (verified live against 4 real
queries) - usually the exact app someone typed, so this would have broken
the single most common search. Fix reads the actual search page HTML for
the first store listing link instead of the library's broken internal
JSON index. `search_apps()` + `_recover_top_result_app_id()` in
`motor/sources/google_play.py`, full TDD cycle, 8 new tests. Routes are
thin wrappers over already-tested `motor/` functions, writing to the same
`scripts/output/` paths the terminal workflow already uses. Also added
`CLAUDE.md` rule 6: explain the reasoning and impact of every suggestion
or action, in plain language, live in the conversation - Matheus's own
framing is that this project is a learning vehicle for him as much as
it's software.

### `75f11ee` — Document sampling/enrichment decisions, promote Opportunity Report pattern (2026-08-09)
Registered two already-made-but-undocumented architecture decisions with
their motivation, in the two places meant to be the living reference (not
just this log): `CLAUDE.md`'s Architecture decisions section and
`README.md` §4. Promoted the Product Opportunity Report pattern -
validated against a real 36-review Hevy batch and approved via a
published artifact - from a one-off scratchpad script into tested
`motor/pipeline/report.py` code: `classify_theme()` (Pain/Strength/Mixed),
`OpportunitySummary`, `summarize_opportunities()`, wired into
`assemble_report()`. Full TDD cycle, 13 new tests, 79/79 passing.
Spot-checked the promoted logic against the artifact's real numbers
(bug-reports -> pain, fix-health-connect-sync as top opportunity) to
confirm it reproduces what Matheus already reviewed. The actual HTML
dashboard template stays out of scope (DAY 6).

### `a8a322c` — Add docs/how-to-test.md (2026-08-08)
Wrote the standing, non-technical Parts A→B→C→D walkthrough for the
manual-labeling loop, documenting the `POOL_SIZE`/`SAMPLE_SIZE`/
`RATING_FILTER` constants added in the previous commit, how to read the
report's `count`/`positive`/`negative`/`neutral`/`feature_requests`
fields, and why sampling can't be truly random (Google Play has no
random-access API - confirmed by reading the installed library's source).
Linked from `README.md`. Also caught and fixed two stale spots in
`CLAUDE.md`'s folder tree (`scripts/` and `selection.py` were missing).

### `ad5442e` — Add configurable pool size, random subsampling, rating filter (2026-08-08)
Matheus, testing the dashboard's underlying data live, asked three sharp
questions: is the sample actually random, can sample size be configured,
can we filter by star rating? Investigated the real constraint first
(`google_play_scraper` has no random-access mode, only sort-by-newest/
relevant/rating, with a 4500-per-request internal ceiling) before
proposing anything. Landed on: `collect()` gets a configurable `count`
(pool size, default raised 100→300, still one bounded request), a new
adapter-agnostic `motor/pipeline/selection.py` (`random_sample`,
`filter_by_rating`) that works on any `ReviewSource`'s output, and a
corrected `BIAS_DISCLAIMER` that now discloses the recency bias which was
silently present before and never disclosed. Full TDD cycle: tests
written and approved first, then implementation. Verified live against
real Hevy data with a `[1, 2]` rating filter - only 1-2★ reviews came
through as expected.

### `0a36fd5` — Fix truncated quotes and clarify multi-theme repeats (2026-08-05)
While testing the report script by hand, Matheus flagged what looked like
duplicate review text and cut-off quotes. Investigated both: the
"duplicate" was a real review correctly appearing under two themes at
once (intentional, tested behavior in `report.py` - not a bug), but the
truncation (`quote.body[:100]`) was a genuine display bug in the tutorial
script only, not in the tested pipeline. Fixed the truncation and added
`(also tagged: ...)` annotations so the multi-theme case reads as
intentional instead of broken.

### `2236177` — Add scripts/ helpers for the manual-labeling workflow (2026-08-05)
Formalized the collect→export→label→apply loop (previously ad hoc
scratch scripts) into two permanent, simple-path commands:
`scripts/1_collect_and_export.py` and `scripts/3_apply_labels_and_report.py`.
Also fixed a real crash: Windows terminals default to a codepage that
can't print emoji, which real reviews frequently contain - `sys.stdout`
now gets reconfigured to UTF-8 with `errors="replace"`.

### `5e32779` — Document the manual-labeling path as an equal alternative to enrich() (2026-08-05)
Updated `CLAUDE.md` and `README.md` to describe both ways a review gets
labeled (the Anthropic API via `enrich()`, or the free manual path via
`manual_labeling.py`) as equally valid, not one primary and one
fallback. Corrected a folder-tree inaccuracy along the way: `collect.py`
had been planned as a separate pipeline file but was never built that
way - `GooglePlaySource.collect()` does that job instead.

### `e768f95` — Add manual-labeling pipeline stage (2026-08-05)
The billing story: Matheus didn't want a second, metered Anthropic API
bill on top of an existing Claude subscription. Explored two paths first
and ruled both out with evidence rather than assumption: the Claude Agent
SDK requires a metered API key regardless (confirmed against Anthropic's
own docs - third-party products built on it can't use claude.ai/subscription
login); headless `claude -p` **does** run under the subscription login,
but Matheus correctly vetoed wiring that into the product itself as
exactly the kind of thing that policy line exists to prevent. Landed on
his own proposal instead: `export_for_labeling()` writes a
self-describing JSON file meant to be attached to a Claude Code
conversation and labeled by hand; `apply_labels()` merges the results
back via the same `dataclasses.replace` pattern `enrich()` already used.
Full TDD cycle, tests approved before implementation.

### `013c339` — DAY 4: implement collect, normalize, enrich, store, and report stages (2026-08-04)
The DAY 3 test suite (49 tests) was already written and committed;
DAY 4's job was purely to make it pass, nothing more. Implemented
`GooglePlaySource.collect()`, `normalize()`/`deduplicate()`, `enrich()`
(Anthropic API-based), `store()` (idempotent SQLite upsert), and
`report.py`'s `summarize_themes`/`reviews_for_theme`/`compare_apps`/
`assemble_report`. All 49 tests passed on the first implementation pass.
Caught one real bug immediately after: the test fixtures' Hevy package id
(`com.hevy.app`) doesn't actually exist on Google Play - the real one is
`com.hevy` (found via web search, since guessing store IDs is exactly the
kind of thing not to do).

### `15d3b5c`, `4b20258` — Merge + phase tracking update
Housekeeping: merged a remote branch, updated the project's phase
checklist to reflect DAY 3 completion.

### `658bfbe` — DAY 3: TDD test suite (prior session)
Full test suite written before any DAY 4 implementation existed, per the
project's non-negotiable TDD rule - covers collect, normalize, enrich,
store, and report.

### `5ae8df0` — DAY 2: foundation (prior session)
Database schema, the `ReviewSource` port (ports-and-adapters interface),
and the core dataclasses (`Review`, `Project`, `App`).

### `f4dfbe9` — Translate CLAUDE.md to English, add business-friendly README (prior session)
Established the project's dual-audience documentation style: CLAUDE.md
for engineering rules, README.md written for a non-technical reader with
"In plain terms" callouts throughout.

### `e6872a8` — DIA 1: sandbox e governanca (prior session)
Governance and PII policy (`docs/governanca.md`), `.gitignore`,
`.env.example` - no collection code yet, by design.

---

## Project state snapshot (as of `a8a322c`)

- **Pipeline stages implemented:** collect (`GooglePlaySource`), normalize,
  selection (random sample + rating filter), enrich (two interchangeable
  paths: paid API or free manual labeling), store, report. All backed by
  tests (66 passing as of the last commit).
- **Real-world verified:** the full loop has been run multiple times
  against live Hevy Google Play reviews, not just fixtures - including
  hand-labeling ~100+ real reviews across two separate sessions.
- **Not yet built:** DAY 5 (optimization/scheduling), DAY 6 (the actual
  HTML dashboard - the in-progress Product Opportunity Report work above
  is a preview of this), DAY 7 (CI/CD hardening), DAY 8 (deploy).
- **Key standing decisions:** dark theme + gold (#FFC000) is the
  established visual identity for any dashboard output; manual labeling
  via Claude Code is the default enrichment path, not a fallback; sample
  data is pool-then-random-subsample, always disclosed as recency-biased,
  never presented as a full-population survey.
