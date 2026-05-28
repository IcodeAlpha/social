"""
connectors/linkedin_poster.py
Phase 2 — LinkedIn via LinkedIn API v2

Prerequisites:
  - LinkedIn Developer App (apply at https://developer.linkedin.com)
  - Permissions: w_member_social, r_liteprofile
  - OAuth 2.0 access token

Set env vars:
  LINKEDIN_ACCESS_TOKEN   — OAuth 2.0 bearer token
  LINKEDIN_PERSON_URN     — your URN e.g. "urn:li:person:XXXXXXXXXX"
                            (Get it from /v2/me endpoint)
"""

import os
import json
import base64
import requests
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("linkedin")

LI_BASE = "https://api.linkedin.com/v2"


def _headers():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise EnvironmentError("Set LINKEDIN_ACCESS_TOKEN env var.")
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _get_person_urn() -> str:
    urn = os.environ.get("LINKEDIN_PERSON_URN", "")
    if not urn:
        raise EnvironmentError("Set LINKEDIN_PERSON_URN env var.")
    return urn


def _register_image_upload() -> tuple[str, str]:
    """
    Register an image upload with LinkedIn.
    Returns (asset_urn, upload_url).
    """
    person_urn = _get_person_urn()
    url = f"{LI_BASE}/assets?action=registerUpload"
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }
    resp = requests.post(url, headers=_headers(), json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    asset_urn   = data["value"]["asset"]
    upload_url  = data["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    logger.info(f"LinkedIn asset registered: {asset_urn}")
    return asset_urn, upload_url


def _upload_image_bytes(upload_url: str, image_path: Path):
    """Upload raw bytes to LinkedIn's upload URL."""
    with open(image_path, "rb") as f:
        data = f.read()
    headers = {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "Content-Type": "application/octet-stream",
    }
    resp = requests.post(upload_url, headers=headers, data=data, timeout=60)
    resp.raise_for_status()
    logger.info("Image bytes uploaded to LinkedIn.")


def _create_share(asset_urn: str, caption: str, hashtags: list[str]) -> str:
    """Create the LinkedIn share post. Returns the share URN."""
    person_urn = _get_person_urn()
    tag_str = " ".join(hashtags)
    full_text = f"{caption}\n\n{tag_str}"[:3000]  # LinkedIn limit

    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": full_text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": caption[:200]},
                        "media": asset_urn,
                        "title": {"text": "AI Generated Post"},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(f"{LI_BASE}/ugcPosts", headers=_headers(), json=body, timeout=30)
    resp.raise_for_status()
    share_urn = resp.json()["id"]
    logger.info(f"LinkedIn post published! URN: {share_urn}")
    return share_urn


def post_to_linkedin(image_path: Path, caption: str, hashtags: list[str]) -> str:
    """
    Post an image + caption to LinkedIn.

    Args:
        image_path: Local path to the image file.
        caption:    Post text.
        hashtags:   List of hashtag strings.

    Returns:
        Share URN string.
    """
    logger.info("Posting to LinkedIn...")
    asset_urn, upload_url = _register_image_upload()
    _upload_image_bytes(upload_url, image_path)
    share_urn = _create_share(asset_urn, caption, hashtags)
    return share_urn


if __name__ == "__main__":
    test_img  = Path("output/test.png")
    test_cap  = "Excited to share this AI-generated insight 🤖"
    test_tags = ["#AI", "#Automation", "#Innovation"]
    if test_img.exists():
        urn = post_to_linkedin(test_img, test_cap, test_tags)
        print(f"LinkedIn URN: {urn}")
    else:
        print("Add a test image at output/test.png first.")
