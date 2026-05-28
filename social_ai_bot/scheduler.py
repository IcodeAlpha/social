"""
scheduler.py
Phase 3 — Full Automation Runner

Reads content_calendar.json, runs the AI pipeline at scheduled times,
and posts to all configured platforms.

Usage:
    python scheduler.py              # run continuously (production)
    python scheduler.py --run-now 1  # immediately run calendar entry with id=1
    python scheduler.py --dry-run    # show schedule without posting
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import schedule

from post_generator import create_post
from utils.logger import get_logger

logger = get_logger("scheduler")

CALENDAR_FILE = Path("content_calendar.json")

# ── Platform poster registry ───────────────────────────────────────────────────
# Import connectors lazily so missing optional deps don't crash startup
def _get_posters():
    posters = {}
    try:
        from connectors.instagram_poster import post_to_instagram, upload_image_imgur
        posters["instagram"] = lambda img, cap, tags: post_to_instagram(
            upload_image_imgur(img), cap, tags
        )
    except Exception as e:
        logger.warning(f"Instagram connector unavailable: {e}")

    try:
        from connectors.twitter_poster import post_to_twitter
        posters["twitter"] = post_to_twitter
    except Exception as e:
        logger.warning(f"Twitter connector unavailable: {e}")

    try:
        from connectors.linkedin_poster import post_to_linkedin
        posters["linkedin"] = post_to_linkedin
    except Exception as e:
        logger.warning(f"LinkedIn connector unavailable: {e}")

    return posters


# ── Core job runner ────────────────────────────────────────────────────────────
def run_calendar_entry(entry: dict, dry_run: bool = False):
    logger.info(f"▶ Running entry id={entry['id']} topic='{entry['topic']}'")

    if dry_run:
        logger.info(f"  [DRY RUN] Would post to: {entry['platforms']}")
        return

    try:
        posts = create_post(
            topic=entry["topic"],
            platforms=entry["platforms"],
            brand_voice=entry.get("brand_voice", "professional yet approachable"),
            extra_instructions=entry.get("extra_instructions", ""),
        )
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return

    posters = _get_posters()
    results = {}

    for platform in entry["platforms"]:
        if platform not in posters:
            logger.warning(f"No connector for '{platform}', skipping.")
            continue

        post_data  = posts[platform]
        image_path = Path(post_data["image_path"])
        caption    = post_data["caption"]
        hashtags   = post_data["hashtags"]

        try:
            result = posters[platform](image_path, caption, hashtags)
            results[platform] = {"status": "ok", "id": result}
            logger.info(f"  ✅ {platform}: posted (id={result})")
        except Exception as e:
            results[platform] = {"status": "error", "error": str(e)}
            logger.error(f"  ❌ {platform}: {e}")

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = Path("output") / f"results_{ts}.json"
    result_file.write_text(json.dumps({"entry": entry, "results": results}, indent=2))
    logger.info(f"Results saved: {result_file}")


# ── Schedule builder ───────────────────────────────────────────────────────────
DAY_MAP = {
    "monday":    schedule.every().monday,
    "tuesday":   schedule.every().tuesday,
    "wednesday": schedule.every().wednesday,
    "thursday":  schedule.every().thursday,
    "friday":    schedule.every().friday,
    "saturday":  schedule.every().saturday,
    "sunday":    schedule.every().sunday,
}


def build_schedule(calendar: list[dict], dry_run: bool = False):
    for entry in calendar:
        time_str = entry.get("scheduled_time", "09:00")
        days     = [d.lower() for d in entry.get("days", ["monday"])]

        for day in days:
            if day not in DAY_MAP:
                logger.warning(f"Unknown day '{day}' in entry {entry['id']}, skipping.")
                continue

            DAY_MAP[day].at(time_str).do(run_calendar_entry, entry=entry, dry_run=dry_run)
            logger.info(f"Scheduled entry {entry['id']} every {day} at {time_str}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AI Social Media Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Print schedule without posting")
    parser.add_argument("--run-now", type=int, metavar="ID", help="Immediately run entry with this ID")
    args = parser.parse_args()

    calendar = json.loads(CALENDAR_FILE.read_text())

    if args.run_now:
        matches = [e for e in calendar if e["id"] == args.run_now]
        if not matches:
            print(f"No calendar entry with id={args.run_now}")
            return
        run_calendar_entry(matches[0], dry_run=args.dry_run)
        return

    build_schedule(calendar, dry_run=args.dry_run)

    if args.dry_run:
        print("\n📅 Scheduled jobs:")
        for job in schedule.jobs:
            print(f"  {job}")
        return

    logger.info("🤖 Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()