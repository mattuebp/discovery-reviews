---
name: product-opportunity-report
description: Build the Discovery Reviews "Product Opportunity Report" — turns a hand-labeled batch of reviews (scripts/output/reviews_raw.json + labels.json) into a Pain/Strength/Growth-Signal HTML dashboard, with opportunities split into In-Product fixes vs. New-Venture (standalone MVP) candidates. Use whenever Matheus asks for a report, dashboard, or opportunity analysis on a labeled review batch.
---

<!--
  This file teaches Claude Code how to build the report the same way every
  time, instead of redesigning it from scratch each session (which is what
  happened twice before this skill existed - see docs/session-history.md,
  commits building toward 75f11ee and this one). Written for Matheus to
  read too: every step says what it does and why, not just what to run.
-->

# Product Opportunity Report

## When to use this

Matheus has a labeled batch (`scripts/output/reviews_raw.json` +
`scripts/output/labels.json`, produced via `webapp/app.py` or
`scripts/1_collect_and_export.py` + manual labeling — see
`docs/how-to-test.md`) and wants it turned into a report or dashboard.

## Step 1 — Compute the data (reuse tested code, don't reinvent it)

```python
from motor.models import Review, App, Project
from motor.pipeline.manual_labeling import apply_labels
from motor.pipeline.report import assemble_report, reviews_for_theme

reviews = [Review(**d) for d in json.load(open("scripts/output/reviews_raw.json", encoding="utf-8"))]
enriched = apply_labels(reviews, "scripts/output/labels.json")
project = Project(name="...", apps=[App(app_id="...", platform="google_play", country="...", role="primary")])
report = assemble_report(project, {app_id: enriched})
```

`assemble_report()` already gives you `pain_themes`, `strength_themes`,
`mixed_themes` (via `classify_theme()`: pain ≥65% negative, strength ≥65%
positive, else mixed) and `opportunities` (via `summarize_opportunities()`,
grouped by `opportunity_tag`, ranked by count). **Do not recompute this
logic by hand in a scratchpad script** — both are unit-tested in
`tests/test_report.py`; a fresh script is exactly how the two earlier
reports each had to redo the same classification logic from scratch.

If a theme/opportunity classification looks wrong when you spot-check it,
the fix belongs in `motor/pipeline/report.py` (with a test), not in the
report-drafting step below.

## Step 2 — Split opportunities into two kinds (new — do this by hand, not in code)

`summarize_opportunities()`'s output is a flat, ranked list. Before writing
the report, **read the top opportunities and their real quotes, and sort
each one into exactly one of two kinds.** This is a judgment call, not a
count or percentage — that's why it happens here, while drafting, and not
as a field computed in `motor/`.

### Kind 1 — In-Product Opportunities
Scoped to the analyzed app's *own* backlog: bugs, sync reliability,
pricing/paywall friction, onboarding friction, UX papercuts, support gaps.

**The test:** would this app's own PM slot it into their next sprint?
If yes, Kind 1.

Typical themes: `bug-reports`, `sync`, `pricing-subscription`,
`performance`, `account-requirement`, `login-issues`, `customer-support`,
`data-entry-ux`, `watch-integration`, `widgets`, `notifications`,
`data-persistence`. Most opportunities in a real batch will land here —
that's normal, not a sign you're doing it wrong.

### Kind 2 — New-Venture Opportunities
Reveals an unmet *user need* bigger than a feature ticket — something that
could be scoped, designed, and validated as its own separate product,
independent of whether the analyzed app ever builds it. This is the kind
that matters for Matheus's own purpose (build-to-learn, portfolio,
possible future MVP), not for the analyzed app's roadmap.

**The test:** if you pitched this as a brand-new, standalone app to a
stranger — not a feature request to this app's support inbox — does it
still make sense on its own? If yes, Kind 2.

**How to find real ones (don't manufacture them):**
- Look for a *cluster* of related opportunity tags/themes pointing at the
  same underlying job-to-be-done, not one isolated tag in isolation. A
  single "add-kettlebell-exercises" request is Kind 1 (exercise-library
  backlog item); several tags together implying "people want structured,
  guided programming, not just a logger" is a genuine Kind 2 candidate.
- Ask whether the need exists *because the category is underserved*, not
  just because this one app is missing a checkbox.
- It is normal and expected for a batch to surface zero, one, or two real
  Kind 2 candidates — do not pad this list to look more productive than
  the data supports (this is the same honesty rule that keeps an empty
  Strengths section empty rather than stretched to fill space).

For every Kind 2 candidate, write: the underlying need in one sentence,
which opportunity tags/quotes support it, and *why* it stands on its own
apart from the analyzed app's roadmap — this is the reasoning-and-impact
habit from `CLAUDE.md` rule 6, applied inside the report itself, not just
in conversation.

## Step 3 — Build the HTML report

Visual identity: dark theme, gold `#FFC000` accent, Bebas Neue (display) +
Barlow (body) — matches `CLAUDE.md`'s "Stack" section and every dashboard
built so far. Self-hosted fonts as base64 `@font-face` data URIs (the
Artifact CSP blocks font CDNs) — download once from Google Fonts, reuse
across sessions, don't re-invent the embedding step.

**Fixed section order** (do not reorder or drop sections just because a
batch is small):

1. Status banner + header (app, sample size, collection method)
2. KPI stat strip (reviews analyzed, feature requests, pain/strength/mixed
   theme counts)
3. Sentiment composition (stacked bar, status colors: good=positive,
   critical=negative, neutral=neutral)
4. **Bias/scope callout** — always state whether the sample was rating-
   filtered. A 1★–3★-only batch will show 0 Strength themes *by
   construction*; say so explicitly next to the sentiment chart, not just
   in a footer footnote (see the two published Hevy reports for the exact
   wording pattern to reuse).
5. Pain Points — all themes, not just the top few. Table for the full
   ranked list (theme, count, sentiment mini-bar, feature-request count);
   quote-card spotlights only for the top 5–6 by volume once a batch gets
   large (>10 pain themes) — don't force a full quote-card per theme past
   that point, it becomes unreadable.
6. Strengths — if empty, use an explicit empty-state box explaining *why*
   (e.g. a rating-filtered sample), never just an empty section.
7. Growth Signals (mixed themes)
8. **In-Product Backlog** (Kind 1 opportunities, ranked by count)
9. **New-Venture Candidates** (Kind 2 — short, curated, reasoning included
   per entry; omit the section header entirely if there are zero genuine
   candidates rather than showing an empty section)
10. All Opportunities — full reference appendix, every tag, ranked
11. "The Pattern, Now In Code" — name the steps above explicitly (keeps the
    report self-documenting)
12. Footer — full methodology, bias disclaimer, what's still not built

## Step 4 — Publish and report back

Publish via the Artifact tool. If this is a re-run for the same
app/analysis, update the *same* artifact URL (pass `url` from
`action: "list"` or the prior publish result) rather than minting a new
one — Matheus has already reviewed and bookmarked the earlier link.

When done, tell Matheus in plain language (per `CLAUDE.md` rule 6): sample
size, headline Pain theme, how many Kind 1 vs. Kind 2 opportunities
surfaced, and any Kind 2 candidate worth a second look.
