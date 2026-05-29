"""
api/index.py
Flask backend for the Social AI Bot demo
Vercel-compatible entry point
"""

import os
import time
import json
import requests
from datetime import datetime
from urllib.parse import quote
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID   = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")


# ── Caption generation ────────────────────────────────────────────────────────

def generate_caption(topic, platform, brand_voice="professional yet approachable"):
    client = genai.Client(api_key=GEMINI_API_KEY)

    platform_rules = {
        "instagram": "Up to 2200 characters. Use emojis. End with a call-to-action. 20-30 hashtags.",
        "twitter":   "Max 280 characters total including hashtags. Be punchy and engaging. 2-3 hashtags only.",
        "linkedin":  "Professional tone. 1300 characters max. No emojis. 3-5 industry hashtags.",
    }
    rules = platform_rules.get(platform, platform_rules["instagram"])

    prompt = f"""
You are a world-class social media copywriter with a {brand_voice} brand voice.

Topic: {topic}
Platform: {platform.upper()}
Platform rules: {rules}

Respond ONLY with a valid JSON object — no markdown fences, no preamble:
{{
  "caption": "<full post caption>",
  "hashtags": ["#tag1", "#tag2"],
  "alt_text": "<one-sentence image description>",
  "image_prompt": "<detailed image generation prompt that visually represents this post>"
}}
""".strip()

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    return json.loads(raw)


# ── Image URL ─────────────────────────────────────────────────────────────────

def get_image_url(image_prompt):
    encoded = quote(image_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"


# ── Instagram posting ─────────────────────────────────────────────────────────

def post_to_instagram(image_url, caption, hashtags, access_token, account_id):
    full_caption = f"{caption}\n\n{' '.join(hashtags)}"
    GRAPH = "https://graph.facebook.com/v19.0"

    # Step 1 — create media container
    res = requests.post(f"{GRAPH}/{account_id}/media", json={
        "image_url": image_url,
        "caption": full_caption,
        "access_token": access_token,
    })
    data = res.json()
    if not res.ok or "error" in data:
        raise Exception(data.get("error", {}).get("message", "Container creation failed"))

    container_id = data["id"]

    # Step 2 — wait for image to be ready, then publish
    time.sleep(8)

    pub = requests.post(f"{GRAPH}/{account_id}/media_publish", json={
        "creation_id": container_id,
        "access_token": access_token,
    })
    pub_data = pub.json()
    if not pub.ok or "error" in pub_data:
        raise Exception(pub_data.get("error", {}).get("message", "Publish failed"))

    return pub_data["id"]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("../../", "index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    topic        = data.get("topic", "").strip()
    platforms    = data.get("platforms", ["instagram", "twitter", "linkedin"])
    brand_voice  = data.get("brand_voice", "professional yet approachable")
    post_to_ig   = data.get("post_to_instagram", False)

    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 500

    try:
        posts = {}
        image_prompt = None

        for platform in platforms:
            result = generate_caption(topic, platform, brand_voice)
            posts[platform] = result
            if image_prompt is None:
                image_prompt = result["image_prompt"]

        image_url = get_image_url(image_prompt)

        for platform in posts:
            posts[platform]["image_url"] = image_url

        # Instagram auto-post
        instagram_result = {"status": "not_requested"}

        if post_to_ig and "instagram" in posts:
            if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
                instagram_result = {
                    "status": "error",
                    "error": "INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID not set in .env",
                }
            else:
                try:
                    media_id = post_to_instagram(
                        image_url,
                        posts["instagram"]["caption"],
                        posts["instagram"]["hashtags"],
                        INSTAGRAM_ACCESS_TOKEN,
                        INSTAGRAM_ACCOUNT_ID,
                    )
                    instagram_result = {"status": "posted", "media_id": media_id}
                except Exception as e:
                    instagram_result = {"status": "error", "error": str(e)}

        return jsonify({
            "success": True,
            "topic": topic,
            "posts": posts,
            "image_url": image_url,
            "instagram": instagram_result,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "gemini": bool(GEMINI_API_KEY),
        "instagram": bool(INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)