"""
post_generator.py
Phase 1 — Core AI Agent
- Gemini AI  → caption + hashtags  (google-genai SDK)
- DALL·E 3   → image
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from google import genai
from utils.logger import get_logger
from urllib.parse import quote

logger = get_logger("post_generator")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_caption(
    topic: str,
    platform: str = "instagram",
    brand_voice: str = "professional yet approachable",
    extra_instructions: str = "",
) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    platform_rules = {
        "instagram": "Up to 2200 characters. Use emojis. End with a call-to-action. 20-30 hashtags.",
        "twitter":   "Max 280 characters total including hashtags. Be punchy and engaging. 2-3 hashtags only.",
        "linkedin":  "Professional tone. 1300 characters max. No emojis. 3-5 industry hashtags.",
    }

    rules = platform_rules.get(platform.lower(), platform_rules["instagram"])

    prompt = f"""
You are a world-class social media copywriter with a {brand_voice} brand voice.

Topic: {topic}
Platform: {platform.upper()}
Platform rules: {rules}
{f"Extra instructions: {extra_instructions}" if extra_instructions else ""}

Respond ONLY with a valid JSON object — no markdown fences, no preamble:
{{
  "caption": "<full post caption>",
  "hashtags": ["#tag1", "#tag2"],
  "alt_text": "<one-sentence image description>",
  "image_prompt": "<detailed DALL-E 3 image generation prompt that visually represents this post>"
}}
""".strip()

    logger.info(f"Generating caption for topic='{topic}' platform='{platform}'")
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    result = json.loads(raw)
    logger.info(f"Caption generated: {result['caption'][:60]}...")
    return result


def generate_image(image_prompt: str, save_path=None) -> Path:
    """
    Generate an image using Pollinations.ai — completely free, no API key needed.
    """
    logger.info(f"Generating image: {image_prompt[:80]}...")

    encoded_prompt = quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    if save_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = OUTPUT_DIR / f"image_{timestamp}.png"

    with open(save_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Image saved to {save_path}")
    return save_path


def create_post(
    topic: str,
    platforms=None,
    brand_voice: str = "professional yet approachable",
    extra_instructions: str = "",
) -> dict:
    if platforms is None:
        platforms = ["instagram", "twitter", "linkedin"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = OUTPUT_DIR / f"post_{timestamp}.png"

    posts = {}
    image_prompt = None

    for platform in platforms:
        data = generate_caption(topic, platform, brand_voice, extra_instructions)
        posts[platform] = data
        if image_prompt is None:
            image_prompt = data["image_prompt"]

    img_path = generate_image(image_prompt, save_path=image_path)

    for platform in posts:
        posts[platform]["image_path"] = str(img_path)

    package_path = OUTPUT_DIR / f"post_package_{timestamp}.json"
    with open(package_path, "w") as f:
        json.dump({"topic": topic, "timestamp": timestamp, "posts": posts}, f, indent=2)

    logger.info(f"Post package saved: {package_path}")
    return posts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Social Media Post Generator")
    parser.add_argument("topic", help="Topic or theme for the post")
    parser.add_argument(
        "--platforms", nargs="+",
        default=["instagram", "twitter", "linkedin"],
        help="Platforms to generate for"
    )
    parser.add_argument("--voice", default="professional yet approachable", help="Brand voice")
    parser.add_argument("--extra", default="", help="Extra instructions for Gemini")
    args = parser.parse_args()

    posts = create_post(args.topic, args.platforms, args.voice, args.extra)

    for platform, data in posts.items():
        print(f"\n{'='*50}")
        print(f"  {platform.upper()}")
        print(f"{'='*50}")
        print(data["caption"])
        print("\nHashtags:", " ".join(data["hashtags"]))
        print(f"Image: {data['image_path']}")