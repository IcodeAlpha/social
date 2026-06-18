"""
scheduler.py
Runs 3x daily — posts to Instagram + LinkedIn automatically.
Designed to run 24/7 on Railway.
"""

import os
import time
import json
import logging
import requests
import schedule
from datetime import datetime
from urllib.parse import quote
from dotenv import load_dotenv
from google import genai

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scheduler")

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID   = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
LINKEDIN_ACCESS_TOKEN  = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")

# Post times (24hr UTC — 08:00, 13:00, 18:00)
POST_TIMES = ["08:00", "13:00", "18:00"]

# Content calendar — rotates automatically
TOPICS = [
  {"topic":"The baker taught me why small improvements compound into greatness.","voice":"educational and storytelling"},
  {"topic":"I spent years trying to stand out until I learned the power of being useful.","voice":"reflective and educational"},
  {"topic":"The fisherman smiled when everyone else was panicking.","voice":"storytelling and insightful"},
  {"topic":"I thought I needed a new opportunity. I actually needed a new mindset.","voice":"motivational and reflective"},
  {"topic":"The village blacksmith knew more about success than most CEOs.","voice":"storytelling and educational"},
  {"topic":"I asked why he woke up at 4 AM every day. His answer changed my habits.","voice":"inspiring and personal"},
  {"topic":"The most successful person I know never talks about success.","voice":"thought-provoking and reflective"},
  {"topic":"A cracked bucket taught me something perfect never could.","voice":"metaphorical and inspiring"},
  {"topic":"The market vendor spotted an opportunity everyone else ignored.","voice":"storytelling and motivational"},
  {"topic":"I thought luck was random until I watched how he prepared.","voice":"educational and inspiring"},
  {"topic":"The day I stopped waiting for motivation, my life started moving.","voice":"motivational and practical"},
  {"topic":"An empty notebook became the most valuable thing I owned.","voice":"reflective and storytelling"},
  {"topic":"The old carpenter measured twice. His lesson went far beyond wood.","voice":"educational and insightful"},
  {"topic":"I met a millionaire who envied a farmer.","voice":"philosophical and inspiring"},
  {"topic":"The answer wasn't hidden in a book. It was hidden in a routine.","voice":"reflective and educational"},
  {"topic":"A woman carrying water showed me what resilience really means.","voice":"storytelling and emotional"},
  {"topic":"Everyone wanted the spotlight. He mastered the shadows.","voice":"dramatic and motivational"},
  {"topic":"The train left without me, and that's when my journey began.","voice":"storytelling and inspiring"},
  {"topic":"I thought I had missed my chance until I met a 70-year-old beginner.","voice":"inspiring and reflective"},
  {"topic":"The strongest tree in the forest started as the weakest seed.","voice":"metaphorical and motivational"},
  {"topic":"A single notebook page changed the direction of my life.","voice":"personal and inspiring"},
  {"topic":"The baker taught me why small improvements compound into greatness.","voice":"educational and storytelling"},
  {"topic":"I chased certainty and found fear. I chased action and found confidence.","voice":"motivational and reflective"},
  {"topic":"The most important meeting of my life happened by accident.","voice":"storytelling and dramatic"},
  {"topic":"A mechanic explained success using a rusty engine.","voice":"educational and relatable"},
  {"topic":"The roadblock I hated became the shortcut I needed.","voice":"inspiring and reflective"},
  {"topic":"He never won the race, but everyone remembered his journey.","voice":"storytelling and emotional"},
  {"topic":"The old notebook in the attic held a lesson for every generation.","voice":"reflective and philosophical"},
  {"topic":"I thought discipline felt like pressure. It actually felt like freedom.","voice":"educational and motivational"},
  {"topic":"The abandoned building taught me what happens to neglected dreams.","voice":"metaphorical and thought-provoking"},
  {"topic":"A stranger asked me one question I couldn't stop thinking about.","voice":"reflective and personal"},
  {"topic":"The person with the least complained the least.","voice":"thought-provoking and inspiring"},
  {"topic":"I found the courage I was looking for in the middle of failure.","voice":"authentic and motivational"},
  {"topic":"The old farmer laughed when I asked for a shortcut.","voice":"storytelling and educational"},
  {"topic":"Everyone saw a problem. She saw a business.","voice":"entrepreneurial and inspiring"},
  {"topic":"The rain ruined our plans and revealed a better path.","voice":"storytelling and uplifting"},
  {"topic":"I learned more from one honest failure than a hundred easy wins.","voice":"reflective and motivational"},
  {"topic":"The man who owned nothing gave me everything I needed to hear.","voice":"emotional and inspiring"},
  {"topic":"A bridge under construction taught me how growth really works.","voice":"metaphorical and educational"},
  {"topic":"The best investment I ever made cost me nothing.","voice":"thought-provoking and inspiring"},
  {"topic":"He kept showing up long after everyone else disappeared.","voice":"dramatic and motivational"},
  {"topic":"The map was wrong, but the journey was exactly right.","voice":"storytelling and reflective"},
  {"topic":"I spent years avoiding discomfort until I discovered its secret.","voice":"motivational and educational"},
  {"topic":"The gardener never dug up the seed to check if it was growing.","voice":"metaphorical and inspiring"},
  {"topic":"The lesson I needed arrived disguised as an inconvenience.","voice":"storytelling and reflective"},
  {"topic":"A child building sandcastles taught me about ambition.","voice":"creative and inspiring"},
  {"topic":"The quietest person in the room changed everyone's future.","voice":"storytelling and dramatic"},
  {"topic":"I asked happiness where it lived. It pointed to gratitude.","voice":"philosophical and reflective"},
  {"topic":"The storm didn't care about my plans, but it improved them anyway.","voice":"inspiring and metaphorical"},
  {"topic":"Nobody noticed him for years. Then they called him an overnight success.","voice":"motivational and storytelling"}
]

topic_index = 0


# ── Caption generation ────────────────────────────────────────────────────────
def generate_caption(topic, platform, brand_voice):
    client = genai.Client(api_key=GEMINI_API_KEY)
    platform_rules = {
        "instagram": "Up to 1500 characters. Use emojis. End with a call-to-action. 5-12 hashtags.",
        "linkedin":  "Professional tone. 1000 characters max. No emojis. 3-5 industry hashtags.",
    }
    prompt = f"""You are a world-class social media copywriter with a {brand_voice} brand voice.
Topic: {topic}
Platform: {platform.upper()}
Platform rules: {platform_rules.get(platform, "")}
Respond ONLY with a valid JSON object — no markdown fences:
{{"caption":"<full post caption>","hashtags":["#tag1","#tag2"],"image_prompt":"<detailed image prompt>"}}""".strip()

    response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip().rstrip("```").strip())


# ── Image ─────────────────────────────────────────────────────────────────────
def get_image_url(image_prompt):
    encoded = quote(image_prompt)
    for url in [
        f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux",
        f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512",
    ]:
        try:
            res = requests.get(url, timeout=60)
            if res.status_code == 200 and "image" in res.headers.get("content-type", ""):
                return url
        except Exception:
            pass
    return f"https://picsum.photos/seed/{abs(hash(image_prompt)) % 1000}/1024/1024"


# ── Instagram ─────────────────────────────────────────────────────────────────
def post_to_instagram(image_url, caption, hashtags):
    GRAPH = "https://graph.facebook.com/v19.0"
    res = requests.post(f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media", json={
        "image_url": image_url,
        "caption": f"{caption}\n\n{' '.join(hashtags)}",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    data = res.json()
    if not res.ok or "error" in data:
        raise Exception(data.get("error", {}).get("message", "Container failed"))
    time.sleep(10)
    pub = requests.post(f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media_publish", json={
        "creation_id": data["id"],
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    pub_data = pub.json()
    if not pub.ok or "error" in pub_data:
        raise Exception(pub_data.get("error", {}).get("message", "Publish failed"))
    return pub_data["id"]


# ── LinkedIn ──────────────────────────────────────────────────────────────────
def post_to_linkedin(caption, hashtags):
    res = requests.get("https://api.linkedin.com/v2/userinfo", headers={
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"
    })
    sub = res.json().get("sub")
    if not sub:
        raise Exception("Could not get LinkedIn URN")

    person_urn = f"urn:li:person:{sub}"
    res = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json={
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": f"{caption}\n\n{' '.join(hashtags)}"[:3000]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
    )
    data = res.json()
    if not res.ok or "serviceErrorCode" in data:
        raise Exception(data.get("message", "LinkedIn post failed"))
    return data.get("id", "posted")


# ── Main job ──────────────────────────────────────────────────────────────────
def run_post():
    global topic_index
    entry = TOPICS[topic_index % len(TOPICS)]
    topic_index += 1
    topic, voice = entry["topic"], entry["voice"]
    log.info(f"Starting post — topic: '{topic}'")

    try:
        ig_data = generate_caption(topic, "instagram", voice)
        li_data = generate_caption(topic, "linkedin", voice)
        log.info("Captions generated")

        image_url = get_image_url(ig_data["image_prompt"])
        log.info(f"Image: {image_url}")

        if INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID:
            try:
                mid = post_to_instagram(image_url, ig_data["caption"], ig_data["hashtags"])
                log.info(f"✅ Instagram posted — {mid}")
            except Exception as e:
                log.error(f"❌ Instagram: {e}")

        if LINKEDIN_ACCESS_TOKEN:
            try:
                pid = post_to_linkedin(li_data["caption"], li_data["hashtags"])
                log.info(f"✅ LinkedIn posted — {pid}")
            except Exception as e:
                log.error(f"❌ LinkedIn: {e}")

    except Exception as e:
        log.error(f"❌ Post cycle failed: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🤖 CIAL.AI Scheduler starting...")
    log.info(f"Post times (UTC): {', '.join(POST_TIMES)}")
    log.info(f"Topics in rotation: {len(TOPICS)}")

    for t in POST_TIMES:
        schedule.every().day.at(t).do(run_post)
        log.info(f"Scheduled: {t} UTC")

    log.info("Waiting for next scheduled post...")
    while True:
        schedule.run_pending()
        time.sleep(30)










