<!--
  This README is written for a non-technical / business reader.
  Every technical term below is followed by an "In plain terms:" line that
  explains what it means and why it matters — no coding background assumed.
-->

# Discovery Reviews

## 1. What this is, and why

**Discovery Reviews** is a system that reads public app-store reviews,
figures out what users are actually complaining about or asking for, and
turns that into a dashboard a Product Manager can use to decide what to build
next.

It's a **build-to-learn portfolio project** by Matheus Prais — a hands-on way
to demonstrate product + engineering thinking, not a commercial product. It
is **not affiliated with, endorsed by, or built on behalf of** any app it
analyzes.

The first app studied is **Hevy** (a strength-training app), chosen simply as
a realistic example. The system itself is built to work for **any app**, not
just Hevy.

> **In plain terms:** imagine paying someone to read every public review of
> your app (or a competitor's), sort the complaints into categories, and
> hand you a one-page summary of "here's what people want." This project
> automates that job.

---

## 2. The problem it solves

Public app reviews contain real signal about what users want — but they're
messy: thousands of short, unstructured, repetitive texts, in different
languages, with lots of noise ("great app!", "5 stars"). No PM has time to
read all of them by hand, and reading only the newest 20 reviews gives a
skewed, unreliable picture.

This project turns that raw pile of text into structured, countable product
insight: which themes come up most, whether feedback is a bug report or a
feature request, and where the product might be losing users versus a
competitor.

---

## 3. How it works — the pipeline

The system processes reviews in **5 sequential stages**. Each stage does one
job and can be tested independently before moving to the next.

1. **Collect** — pulls reviews for an app from its public store page.
   > **In plain terms:** like a research assistant visiting the app's page
   > and copying down every visible review.
2. **Normalize** — converts every review into one consistent format,
   regardless of where it came from, and removes duplicates seen in earlier
   runs.
   > **In plain terms:** making sure every review is filed the same way,
   > with no review counted twice.
3. **Enrich** — an AI (Claude) reads each review and tags it: what topic
   it's about, whether the tone is positive/negative/neutral, whether it's
   really a feature request in disguise, and groups similar complaints
   together.
   > **In plain terms:** the AI plays the role of an analyst skimming every
   > review and sorting it into labeled piles, at a scale no human could do
   > by hand.
4. **Store** — saves everything to a database, safely re-running without
   creating duplicate entries.
   > **In plain terms:** filing the labeled reviews into a cabinet you can
   > search later, without accidentally filing the same paper twice.
5. **Report** — adds everything up into insights ("32% of negative reviews
   mention sync issues") and product opportunities, and produces the data
   behind the dashboard.
   > **In plain terms:** turning the filed reviews into the actual summary
   > slide a PM would present.

---

## 4. Key design decisions (and why they matter)

### Ports and adapters
The system talks to review sources (Google Play today, Apple's App Store
later) through one shared, neutral interface. Each store has its own
"adapter" that plugs into that interface.

> **In plain terms:** think of a universal power adapter. The *system*
> speaks one language internally; each *adapter* is a translator plug for a
> specific store. Adding App Store support later means writing one new
> translator — the rest of the system doesn't need to change.

### App-agnostic engine, "central app vs. competitor" as just a label
The engine doesn't hardcode "Hevy" anywhere. An analysis is set up as one
**primary app** plus any number of **competitor apps**, and the exact same
analysis logic runs on all of them. "Primary" vs. "competitor" is just a tag
used when the final report is assembled — the competitive section is nothing
more than the same analysis, run on the competitors, and read through the
primary app's lens.

> **In plain terms:** the engine doesn't know or care which app is "yours."
> You could point it at any two fitness apps and it would treat them
> identically until the very last step, where it labels one "you" and the
> rest "competitors" for the report.

### One canonical data shape
No matter which store a review came from, it gets converted into the exact
same structured record before anything else happens to it.

> **In plain terms:** like converting every currency to dollars before doing
> math on them. It's what lets the system eventually combine Google Play and
> App Store reviews into one unified analysis instead of two separate ones.

---

## 5. Tech stack — what each piece is for

| Piece | What it's for, in plain terms |
|---|---|
| **Python + pytest** | The programming language the engine is built in, and the tool used to write automated checks that catch bugs before they ship. |
| **google-play-scraper** | The library that actually fetches public review data from Google Play. |
| **SQLite** | A simple, single-file database — no server to set up. Good enough for a project this size; a heavier database (Postgres) is a possible future upgrade if the project grows. |
| **Claude (Anthropic API)** | The AI model that reads and labels each review (the "enrich" stage). |
| **sentence-transformers** (planned) | A free, local tool that measures how *similar in meaning* two pieces of text are — used to group different wordings of the same complaint together (e.g. "syncing is broken" and "my data won't sync" end up in the same bucket). |
| **Self-contained HTML dashboard** | The final output: a single HTML file (dark theme, gold accents) that displays the insights — no app install or server needed to view it. |

---

## 6. Data governance & methodology

Full policy lives in [`docs/governanca.md`](docs/governanca.md); this section
explains the *methodology* behind it in plain language.

- **Public-feed-only collection.** The system only reads reviews that are
  already visible to any visitor on the app's public store page — no login,
  no private or paid API, nothing behind a wall.
  > **In plain terms:** it only reads what anyone browsing the store could
  > already see with their own eyes.

- **Low request rate, with backoff.** The system waits between requests
  instead of firing them as fast as possible, and if the store's servers
  show any sign of pushback, it waits even longer before trying again.
  > **In plain terms:** it behaves like a polite visitor, not a flood of
  > traffic — both out of respect for the store's servers and to avoid
  > getting blocked.

- **No anti-bot evasion.** The system never disguises itself as a real
  browser with fake headers, never rotates IP addresses to dodge a block,
  and never auto-solves CAPTCHAs to force its way past a barrier.
  > **In plain terms:** if the store tries to stop automated access, the
  > system stops — it doesn't try to sneak past. That's a deliberate ethical
  > line, not just a technical limitation.

- **PII pseudonymization.** A review's author is personal data (PII). Before
  anything is stored, the author's identity is passed through a one-way hash
  function and only that hash (`author_hash`) is kept — the original
  identity is never written to disk and cannot be recovered from what's
  stored.
  > **In plain terms:** it's like shredding someone's name and keeping only
  > a fingerprint of the shreds — you can check two fingerprints match, but
  > you can't reconstruct the name from the fingerprint.

- **Secrets handling.** Real API keys live only in a local `.env` file that
  is never committed to version control; a `.env.example` file with the
  variable *names* (but no real values) is committed instead, as a template.
  > **In plain terms:** the "password" template is public so anyone can see
  > what's needed to run the project; the actual password never is.

---

## 7. Methodological honesty

The reviews collected are a **biased sample**: only users motivated enough to
write a public review are represented, which skews toward strong opinions
(very happy or very frustrated) and away from the silent majority. Every
report and metric this system produces must make that limitation explicit,
and no number is ever presented as if it represented the entire user base.

> **In plain terms:** this tells you what vocal reviewers think, not what
> every user thinks — and the project is upfront about that distinction
> everywhere it reports a number.

---

## 8. Project status

Built in phases, roughly one focus area per working session:

- ✅ Problem definition
- ✅ Sandbox setup — isolation & governance (this stage)
- ⬜ Foundation — data model & source interface
- ⬜ Tests written (test-driven development)
- ⬜ Core implementation
- ⬜ Optimization & background jobs
- ⬜ Output dashboard
- ⬜ CI/CD & quality pipeline
- ⬜ Deploy

---

*For the day-to-day engineering rules this project follows (testing
discipline, architecture rules, etc.), see [`CLAUDE.md`](CLAUDE.md).*
