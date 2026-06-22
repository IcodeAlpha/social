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
  {"topic":"Emergence explains more of reality than intention.","voice":"complexity-science and philosophical"},
  {"topic":"The most powerful systems are invisible because they no longer require decisions.","voice":"systems-thinking and philosophical"},
  {"topic":"Complexity grows gradually, collapse happens suddenly.","voice":"complexity-science and analytical"},
  {"topic":"Every optimization creates a new bottleneck somewhere else.","voice":"systems-thinking and educational"},
  {"topic":"Most organizations fail because information travels slower than reality.","voice":"organizational-theory and insightful"},
  {"topic":"The map slowly becomes more important than the territory.","voice":"philosophical and analytical"},
  {"topic":"Scale changes the nature of problems, not just their size.","voice":"systems-thinking and educational"},
  {"topic":"The strongest feedback loops are the ones you cannot see.","voice":"systems-thinking and thought-provoking"},
  {"topic":"Information abundance creates wisdom scarcity.","voice":"information-theory and philosophical"},
  {"topic":"Knowledge isn't power. Bandwidth is.","voice":"information-theory and educational"},
  {"topic":"Most communication failures are compression failures.","voice":"technical and insightful"},
  {"topic":"Intelligence is partly the ability to ignore information.","voice":"cognitive-science and educational"},
  {"topic":"Attention is an economic resource disguised as a psychological one.","voice":"economics and thought-provoking"},
  {"topic":"Every breakthrough begins as an information asymmetry.","voice":"business and analytical"},
  {"topic":"The highest leverage skill is reducing uncertainty.","voice":"decision-science and practical"},
  {"topic":"Good decisions can produce bad outcomes.","voice":"decision-science and educational"},
  {"topic":"Most people confuse confidence with probability.","voice":"critical-thinking and educational"},
  {"topic":"Every decision is a bet whether you admit it or not.","voice":"probability and practical"},
  {"topic":"The future belongs to people who can think probabilistically.","voice":"mathematical and inspiring"},
  {"topic":"Rationality is mostly about updating, not intelligence.","voice":"psychology and analytical"},
  {"topic":"Prediction is overrated. Adaptation is underrated.","voice":"strategic and educational"},
  {"topic":"Success often comes from avoiding catastrophic mistakes rather than making brilliant moves.","voice":"decision-science and insightful"},
  {"topic":"Your opportunities are determined more by network topology than talent.","voice":"network-science and thought-provoking"},
  {"topic":"Success spreads through networks like a virus.","voice":"network-science and educational"},
  {"topic":"Influence is an emergent property, not a personal trait.","voice":"social-science and analytical"},
  {"topic":"Trust is humanity's most scalable technology.","voice":"social-systems and insightful"},
  {"topic":"Reputation is a distributed database.","voice":"technical and philosophical"},
  {"topic":"Every institution is a solution to an information problem.","voice":"systems-thinking and educational"},
  {"topic":"Most power comes from controlling coordination, not resources.","voice":"political-economy and thought-provoking"},
  {"topic":"Incentives are stronger than values in large systems.","voice":"economics and analytical"},
  {"topic":"Markets are prediction engines disguised as economic systems.","voice":"economics and educational"},
  {"topic":"Every company is fundamentally an information-processing machine.","voice":"business and technical"},
  {"topic":"The wealthiest organizations are often the best learning systems.","voice":"business and systems-thinking"},
  {"topic":"Competition is often a battle between feedback loops.","voice":"business and analytical"},
  {"topic":"The real product of most companies is behavior change.","voice":"business and insightful"},
  {"topic":"Most monopolies begin as superior coordination mechanisms.","voice":"economics and thought-provoking"},
  {"topic":"The strongest competitive advantage is adaptation speed.","voice":"strategy and educational"},
  {"topic":"The economy rewards leverage more than effort.","voice":"economics and practical"},
  {"topic":"Every technology is ultimately a force multiplier.","voice":"technology and philosophical"},
  {"topic":"Automation doesn't remove work. It changes where complexity lives.","voice":"technology and analytical"},
  {"topic":"The history of technology is the history of abstraction.","voice":"technical and educational"},
  {"topic":"Software is accumulated human decisions encoded into machines.","voice":"technical and reflective"},
  {"topic":"Every abstraction leaks eventually.","voice":"engineering and educational"},
  {"topic":"The most valuable engineers reduce complexity, not write code.","voice":"technical and insightful"},
  {"topic":"The future will be built by people who understand both humans and systems.","voice":"technology and inspiring"},
  {"topic":"Most failures are coordination failures masquerading as technical failures.","voice":"technical and analytical"},
  {"topic":"Emergence explains more of reality than intention.","voice":"complexity-science and philosophical"},
  {"topic":"The universe rewards compounding but punishes linear thinking.","voice":"mathematical and thought-provoking"},
  {"topic":"Second-order effects determine first-order success.","voice":"strategic and educational"},
  {"topic":"The hardest problems aren't complicated. They're complex.","voice":"complexity-science and educational"}
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



