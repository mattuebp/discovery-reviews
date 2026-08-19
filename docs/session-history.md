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

## In progress — not yet committed (as of 2026-08-09)

**App search + collect interface, plus a "explain reasoning live" rule.**
Matheus, testing the tool by hand, had to look up an app's Google Play
package id manually before he could use it. He asked for a real interface:
type a name, see live suggestions, click to pick one, filter by star
rating, download the file the manual-labeling workflow needs next.

- Investigated `google_play_scraper.search()` before building anything on
  top of it, and found a genuine bug: it loses the app id specifically for
  Google's "exact match" top result card - verified live against 4 real
  queries (Hevy, Strava, MyFitnessPal, Notion). That top card is usually
  the exact app someone typed, so this would have broken the single most
  common search. Root cause and fix, both verified live: the card's ID
  lives at a different spot than the library reads; re-fetching the same
  search page as plain HTML and taking the first
  `store/apps/details?id=...` link on it reliably recovers the real id,
  without depending on the library's (broken) internal JSON indices.
  Landed in `motor/sources/google_play.py` as `search_apps()` +
  `_recover_top_result_app_id()`, full TDD cycle, 8 new tests.
- Built `webapp/` - the project's first running interface (a small local
  Flask app), presented as a genuine architecture choice against a
  terminal-picker alternative before building either. Routes are thin
  wrappers over already-tested `motor/` functions (same convention as
  `scripts/`), writing to the exact same `scripts/output/` paths so the
  existing Part C/D manual-labeling flow keeps working unchanged
  regardless of which front door collected the reviews. Smoke-tested live
  end to end (search + collect) against real Google Play data, not just
  mocks.
- Also added a new standing rule (`CLAUDE.md` rule 6): explain the
  reasoning and impact of every suggestion/action, in plain language, live
  in the conversation - not only in written docs. Matheus's own framing:
  this project is a learning vehicle for him as much as it's software.

`docs/how-to-test.md` Part B now recommends the web app, keeping the
terminal-script instructions as the manual fallback. `CLAUDE.md`'s folder
tree updated to include `webapp/`.

---

## Commit log

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
