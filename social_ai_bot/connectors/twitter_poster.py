"""
connectors/twitter_poster.py
Phase 2 — X (Twitter) via Twitter API v2

Prerequisites:
  - Twitter Developer account (Basic plan, ~$100/mo, required for posting)
  - App with Read + Write permissions
  - OAuth 1.0a credentials

Set env vars:
  TWITTER_API_KEY
  TWITTER_API_SECRET
  TWITTER_ACCESS_TOKEN
  TWITTER_ACCESS_TOKEN_SECRET
"""

import os
import mimetypes
from pathlib import Path
import tweepy
from utils.logger import get_logger

logger = get_logger("twitter")


def _get_client():
    required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing Twitter env vars: {', '.join(missing)}")

    # v1.1 auth (needed for media upload)
    auth = tweepy.OAuth1UserHandler(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    api_v1 = tweepy.API(auth)

    # v2 client (for posting tweets)
    client_v2 = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    return api_v1, client_v2


def post_to_twitter(
    image_path: Path,
    caption: str,
    hashtags: list[str],
) -> str:
    """
    Post a tweet with an image.

    Twitter rules:
      - 280 chars total (caption + space + hashtags)
      - We trim caption to fit if needed.

    Returns:
        Tweet ID (string).
    """
    api_v1, client_v2 = _get_client()

    # Build text within 280-char limit
    tag_str = " ".join(hashtags[:3])   # Twitter: max 2-3 tags recommended
    max_caption = 280 - len(tag_str) - 1
    text = f"{caption[:max_caption]} {tag_str}".strip()

    # Upload media via v1.1 (v2 media upload not yet stable)
    logger.info(f"Uploading image to Twitter: {image_path}")
    media = api_v1.media_upload(filename=str(image_path))
    media_id = media.media_id_string
    logger.info(f"Media uploaded, ID: {media_id}")

    # Post tweet
    logger.info("Posting tweet...")
    response = client_v2.create_tweet(text=text, media_ids=[media_id])
    tweet_id = str(response.data["id"])
    logger.info(f"Tweet posted! ID: {tweet_id}")
    return tweet_id


if __name__ == "__main__":
    # Quick smoke test
    test_img  = Path("output/test.png")
    test_cap  = "My AI bot just posted this automatically 🤖"
    test_tags = ["#aibot", "#automation"]
    if test_img.exists():
        tid = post_to_twitter(test_img, test_cap, test_tags)
        print(f"Tweet ID: {tid}")
    else:
        print("Add a test image at output/test.png first.")
