# CLAUDE.md — Discovery Reviews

> This file is the project's constitution. Claude Code reads it every session.
> Rules here take precedence over convenience.

## What this project is

An engine that collects public app reviews, extracts insights and product
opportunities, and delivers a dashboard for a PM to act on. It's a
**build-to-learn** project and a **portfolio** piece by Matheus Prais. Not
affiliated with any analyzed app.

The initial case study is the app **Hevy** (strength training), but the
system is designed to work for **any app**.

---

## ⚠️ Non-negotiable rules (apply in EVERY session)

1. **TDD is mandatory.** Write failing tests BEFORE any implementation. Do
   NOT write production code until Matheus approves the tests. Any
   implementation without a test will be rejected.
2. **Align before executing.** Propose the plan and wait for approval before
   creating or editing files (use plan mode). This project values discussion
   before building.
3. **No premature optimization.** On coding days (DAY 4), the focus is
   passing tests. Optimization, jobs, and refactoring only happen on DAY 5.
4. **Data governance.** Public feed only, low request rate, no anti-bot
   evasion. A review's author is PII → pseudonymize it. Secrets only in
   `.env` (never committed). See `docs/governanca.md`.
5. **Methodological honesty.** Never fabricate metrics. The review sample is
   biased; code and reports must make that explicit.

---

## Architecture decisions

- **Ports and adapters.** A neutral `ReviewSource` interface defines the
  collection contract. Today only `GooglePlaySource` exists. The App Store
  adapter comes later, without touching the rest of the system.
- **App-agnostic + analysis project.** The system analyzes any app. An
  "analysis project" has one **primary** app + N **competitors**. The engine
  treats them all the same; "primary vs. competitor" is just a role (flag).
  Only report assembly uses that role: the competitive section is the same
  analysis run on the competitors, viewed through the primary app's lens.
- **Platform-neutral canonical schema.** Every adapter returns the same
  review record. That's what allows combining Google + App Store data in the
  future.

---

## Stack

- **Engine:** Python. Tests with **pytest**. Collection with
  **google-play-scraper**.
- **Database:** SQLite (single file, simple) — enough for build-to-learn.
  Postgres remains a future option.
- **Enrichment:** LLM (Claude) labels each review with
  theme/sentiment/feature-request/opportunity-tag. Two interchangeable
  implementations produce identical output, so `store`/`report` never know
  which one ran:
  - `motor/pipeline/manual_labeling.py` (`export_for_labeling` +
    `apply_labels`) — the default for this project's scale. Writes reviews
    to a self-describing JSON file, labeled by hand (or by attaching it to
    a Claude Code conversation, using a Claude subscription instead of a
    separate metered key), then merges the results back in.
  - `motor/pipeline/enrich.py` (`enrich()`) — calls the Anthropic API
    directly for full, unattended automation. Requires `ANTHROPIC_API_KEY`
    and its own separate billing — a DAY 5+ concern (scheduled jobs), not
    required before then.
  - Semantic grouping of similar-wording complaints into one canonical
    candidate (via embeddings, e.g. "syncing is broken" / "my data won't
    sync" → one bucket) is still planned, not yet implemented — library to
    be decided (recommendation: local, free `sentence-transformers`).
- **Dashboard:** self-contained HTML (dark theme, gold #FFC000, Bebas Neue +
  Barlow — same style as the prototype already built). Reads the data the
  report stage generates.
- **Structure:** monorepo.
- **Language:** code identifiers in **English** (international portfolio
  standard); review text preserves its original language; docs and comments
  can be in English or Portuguese depending on audience. (If you'd rather
  have everything in Portuguese, just say so.)

---

## Pipeline (5 stages — each independently testable)

1. **collect** — pulls reviews for an app via an adapter.
2. **normalize** — converts to the canonical schema, generates a dedup key,
   removes duplicates across runs.
3. **enrich** — labels each review (themes, sentiment, feature-request flag,
   opportunity tag), via either `enrich()` (Anthropic API, needs a key) or
   `manual_labeling.py`'s export/apply-labels pair (no key needed — labeled
   through an attached Claude Code conversation instead). Both write the
   same four fields onto `Review`, so nothing downstream cares which one
   ran. Grouping similar-wording complaints into one canonical candidate
   (via embeddings) is still planned, not yet built.
4. **store** — persists to the database idempotently.
5. **report** — aggregates into insights + opportunities and generates the
   dashboard data.

---

## Data contract — Canonical review

Every adapter returns this record:

| field | description |
|---|---|
| `dedup_id` | hash of platform+app+author+date+text |
| `platform` | `google_play` \| `app_store` |
| `app_id` | store package / id |
| `country` | storefront (e.g. `br`) |
| `rating` | 1–5 |
| `title` | title (can be empty on Google Play) |
| `body` | review text |
| `author_hash` | **pseudonymized PII** — never store the raw author |
| `app_version` | reviewed app version |
| `review_date` | ISO 8601 |
| `helpful_votes` | "helpful" votes |
| `dev_reply` | developer reply (text or null) |
| `lang` | detected language |
| `collected_at` | collection timestamp |

Enrichment fields (added at the `enrich` stage):
`themes[]`, `sentiment`, `is_feature_request`, `opportunity_tag`.

---

## Folder structure

```
discovery-reviews/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example            # variable template (never commit the real .env)
├── pyproject.toml          # engine dependencies
├── docs/
│   ├── governanca.md       # DAY 1: PII, ToS, sandbox
│   ├── how-to-test.md      # non-technical, step-by-step manual-labeling walkthrough
│   ├── session-history.md  # narrative changelog - read first when resuming work
│   ├── contrato-dados.md   # canonical review schema
│   └── plano-8-dias.md
├── motor/                  # Python backend
│   ├── __init__.py
│   ├── sources/            # adapters (ports & adapters)
│   │   ├── __init__.py
│   │   ├── base.py         # ReviewSource interface (abstract)
│   │   └── google_play.py  # GooglePlaySource - collect() lives here, not in pipeline/
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── normalize.py
│   │   ├── selection.py        # random_sample() + filter_by_rating(), adapter-agnostic
│   │   ├── enrich.py           # AI labeling via the Anthropic API (needs a key)
│   │   ├── manual_labeling.py  # AI labeling with no API key (export_for_labeling + apply_labels)
│   │   ├── store.py
│   │   └── report.py
│   ├── models/             # dataclasses: Review, Project, App
│   │   └── __init__.py
│   └── db/
│       └── schema.sql      # DAY 2: database creation
├── scripts/                # thin, untested wrappers around motor/ - no logic of their own
│   ├── 1_collect_and_export.py       # collect -> normalize -> filter/sample -> export
│   ├── 3_apply_labels_and_report.py  # apply_labels -> print theme/opportunity report
│   └── output/              # gitignored - collected data never goes into git
├── dashboard/              # self-contained HTML (DAY 6 output)
│   └── template.html
├── contrato/               # shared schemas
│   └── review.schema.json
└── tests/                  # pytest (DAY 3: written BEFORE the code)
    ├── __init__.py
    ├── conftest.py
    ├── test_google_play.py
    ├── test_normalize.py
    ├── test_selection.py
    ├── test_enrich.py
    ├── test_manual_labeling.py
    ├── test_store.py
    └── test_report.py
```

---

## 8-day plan

- **DAY 0 — Problem definition.** Done (see `docs/`).
- **DAY 1 — Sandbox: isolation and governance.** git, `.gitignore`,
  `.env.example`, `docs/governanca.md`, PII policy and ToS posture. No
  collection code.
- **DAY 2 — Foundation.** Monorepo, this CLAUDE.md, database schema,
  `ReviewSource` interface, and models.
- **DAY 3 — TDD.** Write ALL tests before any code.
- **DAY 4 — Code.** Implement until tests pass (no optimizing).
- **DAY 5 — Optimization.** Jobs, heavy processing, refactoring.
- **DAY 6 — Output interface.** Mobile-first HTML dashboard.
- **DAY 7 — Pipeline hardening.** CI/CD, linters, code smells, tests,
  vulnerability scanning.
- **DAY 8 — Deploy.**

---

## Governance & PII (summary — detail in `docs/governanca.md`)

- Public feed/scraper only; low request rate with backoff; no anti-bot
  evasion.
- `author` is never stored raw → store `author_hash` instead.
- `.env` with secrets (`ANTHROPIC_API_KEY`, etc.) never goes into git.
- Database and collected data (`*.db`, `/dados/`) stay out of git.

## Conventions

- Small, descriptive commits. Main branch: `main`.
- No secrets in code or in git history.
- Every file created for this project carries explanatory comments spelling
  out what things are (fields, sections, config keys, etc.) — the project
  owner is non-technical/business background and is using this codebase to
  learn, so files should be self-teaching, not just functional.
- **Update `docs/session-history.md` every time you commit.** Add a new
  entry (newest on top) summarizing what changed and *why* — decisions,
  dead ends, rationale a diff alone won't show. This is what lets work
  continue from a different machine or a fresh conversation without losing
  context; read it first when picking this project back up. If something
  is left mid-flight and uncommitted at the end of a session, note that in
  the "In progress" section at the top before stopping.
