"""STEP 1: pull real reviews for an app and prepare them for AI labeling.

This is a convenience wrapper - it has no real logic of its own, it just
calls the already-tested code in motor/, in order:
  1. GooglePlaySource.collect()   (motor/sources/google_play.py)
  2. normalize() + deduplicate()  (motor/pipeline/normalize.py)
  3. export_for_labeling()        (motor/pipeline/manual_labeling.py)

Edit APP_ID / COUNTRY below to analyze a different app or storefront.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

# Windows terminals default to a codepage that can't print emoji - reviews
# often contain them, so make stdout tolerant instead of crashing.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from motor.sources.google_play import GooglePlaySource
from motor.pipeline.normalize import normalize, deduplicate
from motor.pipeline.manual_labeling import export_for_labeling

APP_ID = "com.hevy"  # the app's real Google Play package id
COUNTRY = "us"  # storefront/country code, e.g. "us", "br"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

source = GooglePlaySource()
raw_reviews = list(source.collect(app_id=APP_ID, country=COUNTRY))
reviews = deduplicate([normalize(r, platform="google_play", app_id=APP_ID, country=COUNTRY) for r in raw_reviews])

# Saved so step 3 can match labels back up without re-collecting (which
# could pull in new reviews and shift the results).
raw_path = OUTPUT_DIR / "reviews_raw.json"
raw_path.write_text(json.dumps([asdict(r) for r in reviews], indent=2, ensure_ascii=False), encoding="utf-8")

export_path = OUTPUT_DIR / "reviews_for_labeling.json"
export_for_labeling(reviews, export_path)

print(f"Done! Collected {len(reviews)} reviews for {APP_ID} ({COUNTRY}).")
print()
print("Now go back to your Claude conversation and say something like:")
print(f'  "Please label the reviews in {export_path}"')
