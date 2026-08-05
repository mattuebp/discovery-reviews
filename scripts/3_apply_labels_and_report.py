"""STEP 3: turn labeled reviews into a theme/opportunity report.

Reads scripts/output/labels.json (saved after Claude labels your reviews)
and scripts/output/reviews_raw.json (written by step 1), merges them with
apply_labels(), then prints the same summary motor/pipeline/report.py will
one day hand to the dashboard.
"""

import json
import sys
from pathlib import Path

# Windows terminals default to a codepage that can't print emoji - reviews
# often contain them, so make stdout tolerant instead of crashing.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from motor.models import Review
from motor.pipeline.manual_labeling import apply_labels
from motor.pipeline.report import summarize_themes, reviews_for_theme

OUTPUT_DIR = Path(__file__).parent / "output"

with open(OUTPUT_DIR / "reviews_raw.json", encoding="utf-8") as f:
    reviews = [Review(**data) for data in json.load(f)]

enriched = apply_labels(reviews, OUTPUT_DIR / "labels.json")
labeled_count = sum(1 for r in enriched if r.themes)
print(f"{labeled_count} of {len(enriched)} reviews are labeled.\n")

print("=== Theme summary ===")
for summary in summarize_themes(enriched):
    print(
        f"{summary.theme:<24} count={summary.count:<3} "
        f"positive={summary.positive} negative={summary.negative} neutral={summary.neutral} "
        f"feature_requests={summary.feature_request_count}"
    )
    for quote in reviews_for_theme(enriched, summary.theme)[:2]:
        tag = f"  [opportunity: {quote.opportunity_tag}]" if quote.opportunity_tag else ""
        other_themes = [t for t in quote.themes if t != summary.theme]
        also_in = f"  (also tagged: {', '.join(other_themes)})" if other_themes else ""
        print(f'    "{quote.body}"{tag}{also_in}')
    print()
