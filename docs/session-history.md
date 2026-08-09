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

## In progress — not yet committed (as of 2026-08-08)

**Product Opportunity Report: pattern drafted, dashboard not yet built.**
Matheus asked for a reusable "prompt pattern" for turning a batch of
enriched reviews into a visual HTML dashboard (ranked pain points by
volume, drill-down into real quotes, charts/tables), to be validated by
him, then folded into `how-to-test.md` / `CLAUDE.md` / `README.md`, and
finally turned into a Skill so every future report follows it automatically.

Status right now:
- A draft pattern doc was written (theme aggregation → Pain/Strength/Mixed
  classification → group by `opportunity_tag` → rank by volume → fixed
  HTML section order) - **not yet shown to or approved by Matheus.**
- A fresh, real 100-review batch was collected and hand-labeled for Hevy
  (`scripts/output/reviews_raw.json` + `labels.json`).
- A one-off script to compute the dashboard's data (theme + opportunity
  aggregation) was written but not finished running.
- **The actual HTML dashboard has not been built yet.** Nothing here is
  committed. Nothing has touched `how-to-test.md`, `CLAUDE.md`, `README.md`,
  or `.claude/skills/` for this feature yet - that's all still pending
  pattern approval, per Matheus's explicit sequencing request.

**Next step when resuming:** finish computing the report data, build the
HTML dashboard from the real Hevy batch already labeled, present both the
pattern and the dashboard together for validation, then proceed to the
doc updates + skill only after approval.

---

## Commit log

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
