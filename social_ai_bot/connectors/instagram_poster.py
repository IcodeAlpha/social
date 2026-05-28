"""
connectors/instagram_poster.py
Phase 2 — Instagram Business via Meta Graph API

Prerequisites:
  - Facebook/Instagram Business account
  - Meta Developer App with instagram_basic + instagram_content_publish permissions
  - Long-lived access token

Set env vars:
  INSTAGRAM_ACCESS_TOKEN   — your long-lived user/page token
  INSTAGRAM_ACCOUNT_ID     — your IG Business account ID (numeric)
"""

import os
import requests
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("instagram")

GRAPH_BASE = "https://graph.facebook.com/v19.0"
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
ACCOUNT_ID   = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")


def _check_config():
    if not ACCESS_TOKEN or not ACCOUNT_ID:
        raise EnvironmentError(
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID env vars."
        )


def _upload_image_container(image_url: str, caption: str) -> str:
    """Step 1: Create a media container and return its ID."""
    url = f"{GRAPH_BASE}/{ACCOUNT_ID}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.post(url, data=params, timeout=30)
    resp.raise_for_status()
    container_id = resp.json()["id"]
    logger.info(f"Instagram media container created: {container_id}")
    return container_id


def _publish_container(container_id: str) -> str:
    """Step 2: Publish the container. Returns the published media ID."""
    url = f"{GRAPH_BASE}/{ACCOUNT_ID}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.post(url, data=params, timeout=30)
    resp.raise_for_status()
    media_id = resp.json()["id"]
    logger.info(f"Instagram post published! Media ID: {media_id}")
    return media_id


def post_to_instagram(image_url: str, caption: str, hashtags: list[str]) -> str:
    """
    Post an image + caption to Instagram Business.

    Args:
        image_url:  A publicly accessible URL to the image.
                    (Upload to S3, Cloudinary, etc. first if you have a local file.)
        caption:    The post caption.
        hashtags:   List of hashtag strings (e.g. ["#ai", "#tech"]).

    Returns:
        Published media ID.
    """
    _check_config()

    full_caption = f"{caption}\n\n{' '.join(hashtags)}"

    logger.info("Posting to Instagram...")
    container_id = _upload_image_container(image_url, full_caption)
    media_id = _publish_container(container_id)
    return media_id


# ── Helper: upload local file to a temp public URL via Imgur (free, no auth) ──
def upload_image_imgur(image_path: Path) -> str:
    """
    Upload a local image to Imgur and return the public URL.
    Useful for dev/testing without S3/Cloudinary.
    """
    IMGUR_CLIENT_ID = os.environ.get("IMGUR_CLIENT_ID", "")
    if not IMGUR_CLIENT_ID:
        raise EnvironmentError("Set IMGUR_CLIENT_ID for local image uploads.")

    with open(image_path, "rb") as f:
        data = f.read()

    resp = requests.post(
        "https://api.imgur.com/3/image",
        headers={"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"},
        files={"image": data},
        timeout=30,
    )
    resp.raise_for_status()
    url = resp.json()["data"]["link"]
    logger.info(f"Image uploaded to Imgur: {url}")
    return url


if __name__ == "__main__":
    # Quick smoke test (needs real creds + a real image URL)
    test_url   = "https://picsum.photos/1024/1024"
    test_cap   = "Testing my AI bot 🤖"
    test_tags  = ["#aibot", "#test", "#automation"]
    media_id = post_to_instagram(test_url, test_cap, test_tags)
    print(f"Posted! Media ID: {media_id}")
