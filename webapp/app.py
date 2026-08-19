"""The project's one running interface: search for an app, pick which star
ratings to include, and download the file the manual-labeling workflow
needs next (see docs/how-to-test.md, Part C).

Deliberately thin - same "no logic of its own" convention as scripts/, so
it isn't separately unit-tested. Every route just calls already-tested
motor/ functions, in the same order scripts/1_collect_and_export.py
already does; this is a friendlier front door onto that same pipeline, not
a new one.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# Windows terminals default to a codepage that can't print emoji - reviews
# often contain them, same fix scripts/1_collect_and_export.py already uses.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from motor.pipeline.manual_labeling import export_for_labeling
from motor.pipeline.normalize import deduplicate, normalize
from motor.pipeline.selection import filter_by_rating, random_sample
from motor.sources.google_play import GooglePlaySource, search_apps

app = Flask(__name__)

# Same bounded-pool size as scripts/1_collect_and_export.py's default -
# one single request, large enough for random_sample() to draw a
# meaningful subsample from (see motor/sources/google_play.py).
POOL_SIZE = 300

OUTPUT_DIR = Path(__file__).parent.parent / "scripts" / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
def index():
    return send_from_directory(Path(__file__).parent / "templates", "index.html")


@app.get("/api/search")
def api_search():
    query = request.args.get("q", "")
    country = request.args.get("country", "us")
    if not query.strip():
        return jsonify([])

    results = search_apps(query, country=country)
    return jsonify([asdict(r) for r in results])


@app.post("/api/collect")
def api_collect():
    body = request.get_json()
    app_id = body["app_id"]
    country = body.get("country", "us")
    ratings = body.get("ratings")  # e.g. [1, 2, 3] or None for "all"
    sample_size = int(body.get("sample_size", 100))

    source = GooglePlaySource()
    raw_reviews = list(source.collect(app_id=app_id, country=country, count=POOL_SIZE))
    reviews = deduplicate(
        [normalize(r, platform="google_play", app_id=app_id, country=country) for r in raw_reviews]
    )

    if ratings:
        reviews = filter_by_rating(reviews, ratings)

    reviews = random_sample(reviews, sample_size)

    # Same output paths scripts/1_collect_and_export.py already writes to,
    # so docs/how-to-test.md's Part C/D (label, then see the report) keep
    # working unchanged no matter which front door collected the reviews.
    raw_path = OUTPUT_DIR / "reviews_raw.json"
    raw_path.write_text(json.dumps([asdict(r) for r in reviews], indent=2, ensure_ascii=False), encoding="utf-8")

    export_path = OUTPUT_DIR / "reviews_for_labeling.json"
    export_for_labeling(reviews, export_path)

    return send_from_directory(
        OUTPUT_DIR, export_path.name, as_attachment=True, download_name="reviews_for_labeling.json"
    )


if __name__ == "__main__":
    print("Discovery Reviews is running at http://127.0.0.1:5000")
    app.run(debug=True)
