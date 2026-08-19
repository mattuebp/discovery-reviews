<!--
  This guide is written for a non-technical reader. No terminal or coding
  experience is assumed. Update this file whenever the underlying scripts
  or workflow change - it should always match what's actually in scripts/.
-->

# How to Test the Application

This is the step-by-step guide for running the review pipeline yourself and
getting reviews labeled by AI, without any paid API key. It uses the
manual-labeling workflow (`motor/pipeline/manual_labeling.py`): pull real
reviews, label them through a Claude Code conversation, feed the results
back in, see the report.

Four parts: **A** open a terminal, **B** pull real reviews, **C** get them
labeled, **D** see the results. Do them in order, every time.

---

## Part A — Open a terminal in the project folder

You'll do this every time, so it's worth learning once.

1. Press **Windows key + E** to open File Explorer.
2. Click into the address bar at the top, type `C:\discovery-reviews`, and
   press **Enter**.
3. You should now see the project's files: `CLAUDE.md`, `README.md`,
   `motor`, `tests`, `scripts`, and so on.
4. Click once on that same address bar again (it highlights the whole
   path in blue), type `powershell`, and press **Enter**.
5. A new window opens - dark background, white text, a blinking cursor.
   That's the terminal, already "standing" inside the project folder.

*(If step 4 doesn't do anything: right-click on empty space inside the
folder window instead, and look for "Open in Terminal" in the menu.)*

---

## Part B — Pull real reviews

**Recommended: the search interface.** No more looking up an app's
Google Play package id by hand.

1. In the terminal, type exactly this and press **Enter**:
   ```
   .venv\Scripts\python.exe webapp\app.py
   ```
2. You'll see `Discovery Reviews is running at http://127.0.0.1:5000` -
   open that address in your browser.
3. Type an app's name in the search box; click the one you mean from the
   dropdown that appears (this is also where you can pick a different
   `Country / storefront`, e.g. `br`).
4. Tick which star ratings to include (all five are checked by default -
   that means no filter, every rating), and set **how many reviews to
   analyze**.
5. Click **Collect & Export**. Your browser downloads
   `reviews_for_labeling.json` - move it into
   `C:\discovery-reviews\scripts\output\` (overwrite the old one if
   there's already one there).
6. Leave the terminal window open (or press Ctrl+C to stop the web app
   once you have your file) - you'll come back to the *terminal* in
   Part D, not the browser.

### Or: the terminal script (same result, no browser)

If you'd rather not use the browser, this does the exact same thing:

1. In the terminal, type exactly this and press **Enter**:
   ```
   .venv\Scripts\python.exe scripts\1_collect_and_export.py
   ```
2. Wait a few seconds. You'll see a summary like:
   ```
   Done! Collected a pool of 300 recent reviews for com.hevy (us),
   filtered/sampled down to 100 reviews to analyze.

   Now go back to your Claude conversation and say something like:
     "Please label the reviews in C:\discovery-reviews\scripts\output\reviews_for_labeling.json"
   ```
3. Leave that terminal window open - you'll come back to it in Part D.

To change what gets collected this way, open `scripts\1_collect_and_export.py`
with Notepad and edit the constants near the top, then save and re-run the
command above:

| Constant | What it controls | Example |
|---|---|---|
| `APP_ID` | Which app, by its real Google Play package id | `"com.hevy"` |
| `COUNTRY` | Which storefront/country | `"us"`, `"br"` |
| `POOL_SIZE` | How many recent reviews to fetch before sampling | `300` |
| `SAMPLE_SIZE` | How many of those to randomly analyze | `100` |
| `RATING_FILTER` | Only look at specific star ratings, or `None` for all | `[1, 2]` for just 1-2 star reviews |

`POOL_SIZE` and `SAMPLE_SIZE` are deliberately two different numbers:
`POOL_SIZE` reviews get fetched (the most recent ones, in one single
request), then `SAMPLE_SIZE` of those get **randomly** picked for actual
analysis - see the "Why random sampling, not just 'most recent'" section
below. (The web app always uses a `POOL_SIZE` of 300 - only `SAMPLE_SIZE`
and the rating filter are exposed there, to keep the page simple.)

---

## Part C — Ask Claude to label them

No terminal needed for this part - just talk to Claude, right here in a
Claude Code conversation.

1. Type a message like: **"Please label the reviews in
   scripts/output/reviews_for_labeling.json"**
2. Claude reads the file directly (nothing to attach or copy-paste), labels
   every review, and saves the results into `scripts\output\labels.json`.
   It'll confirm when done.

---

## Part D — See the results

1. Go back to the terminal window from Part B.
2. Type exactly this and press **Enter**:
   ```
   .venv\Scripts\python.exe scripts\3_apply_labels_and_report.py
   ```
3. You'll see a printed report: each theme that came up, how many reviews
   mention it, how many are positive/negative/neutral, and real quotes with
   any opportunity tags attached.

**To do this again later:** repeat B → C → D. Running Part B again pulls a
fresh pool and overwrites the old files.

---

## Reading the report

Each theme line looks like this:

```
sync                      count=3   positive=0 negative=3 neutral=0 feature_requests=0
```

- **count** - how many reviews were tagged with this theme. A review can
  carry more than one theme, so it's counted under every theme it touches -
  the numbers across all themes can add up to more than the total number
  of reviews analyzed.
- **positive / negative / neutral** - of the reviews tagged with this
  theme, how many read as each tone.
- **feature_requests** - of those, how many are someone explicitly asking
  for something new, not just praising or complaining about what exists.

Under each theme you'll see up to two real quotes. If a quote also appears
under a different theme, you'll see `(also tagged: ...)` next to it -
that's not a duplicate, it's one review that's genuinely about more than
one thing at once (e.g. a review complaining about sync **and** unresponsive
support shows up under both).

---

## Why random sampling, not just "most recent"?

Google Play's own data doesn't support pulling a truly random sample from
every review the app has ever received - only "most recent," "most
relevant," or "by rating," a page at a time. So this project fetches a
bounded pool of the most recent reviews (`POOL_SIZE`), then genuinely
randomizes which ones get analyzed out of that pool (`SAMPLE_SIZE`). Every
report this pipeline produces says so explicitly, in its bias disclaimer:
the sample reflects recently-active, vocal reviewers - not the full,
historical user base. Never read a percentage from this report as if it
represents every user who has ever used the app.

---

## Troubleshooting

- **The terminal shows a wall of red text ending in a Python error.** Copy
  the last ~10 lines and paste them into a Claude Code conversation -
  describe what you were doing when it happened.
- **Emoji in a review crashed the script.** This was a real bug, fixed on
  2026-08-08 - if you see it again, tell Claude, it means something
  regressed.
- **`labels.json` doesn't exist yet when you run Part D.** You skipped Part
  C, or Claude hasn't saved the file yet - ask it directly: "did you save
  labels.json?"

---

*This document should stay in sync with `webapp/app.py`,
`scripts/1_collect_and_export.py`, and `scripts/3_apply_labels_and_report.py`.
If those change, update this file in the same session.*
