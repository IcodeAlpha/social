"""
api/index.py
Flask backend for the Social AI Bot demo
Vercel-compatible entry point
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai

app = Flask(__name__, static_folder="../web/static", template_folder="../web")
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


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

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    return json.loads(raw)


def get_image_url(image_prompt):
    encoded = quote(image_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"


@app.route("/")
def index():
    return send_from_directory("../web", "index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    topic = data.get("topic", "").strip()
    platforms = data.get("platforms", ["instagram", "twitter", "linkedin"])
    brand_voice = data.get("brand_voice", "professional yet approachable")

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

        return jsonify({
            "success": True,
            "topic": topic,
            "posts": posts,
            "image_url": image_url,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "gemini": bool(GEMINI_API_KEY)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
