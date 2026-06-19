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
    {"topic":"The science of compounding is bigger than money.","voice":"analytical and inspiring"},
    {"topic":"A software bug taught me more about leadership than any management book.","voice":"technical and insightful"},
    {"topic":"Why smart people keep making the same mistakes.","voice":"psychology and educational"},
    {"topic":"The hidden algorithm behind almost every successful career.","voice":"systems-thinking and educational"},
    {"topic":"I stopped setting goals and started designing systems.","voice":"practical and analytical"},
    {"topic":"The startup failed because they optimized the wrong metric.","voice":"business and educational"},
    {"topic":"A database outage revealed the biggest weakness in our team.","voice":"technical and reflective"},
    {"topic":"The most dangerous word in decision-making is 'probably'.","voice":"critical-thinking and educational"},
    {"topic":"What machine learning can teach us about personal growth.","voice":"technical and inspiring"},
    {"topic":"The engineer solved a people problem with a systems mindset.","voice":"storytelling and technical"},
    {"topic":"Why feedback loops determine your future.","voice":"systems-thinking and educational"},
    {"topic":"The cost of context switching is higher than most people realize.","voice":"productivity and scientific"},
    {"topic":"The strongest businesses aren't built on products. They're built on habits.","voice":"business and analytical"},
    {"topic":"A network diagram explained success better than a motivational speaker.","voice":"technical and thought-provoking"},
    {"topic":"The mathematics of consistency is surprisingly unfair.","voice":"mathematical and inspiring"},
    {"topic":"Why optimization can secretly destroy progress.","voice":"technical and educational"},
    {"topic":"The engineer who automated himself out of a job became indispensable.","voice":"storytelling and insightful"},
    {"topic":"The concept of technical debt applies to life too.","voice":"technical and reflective"},
    {"topic":"Most people solve symptoms. Experts solve systems.","voice":"systems-thinking and educational"},
    {"topic":"How a queue at a supermarket explains modern productivity.","voice":"analytical and relatable"},
    {"topic":"The invisible bottleneck holding back your growth.","voice":"systems-thinking and practical"},
    {"topic":"A cybersecurity lesson that changed how I make decisions.","voice":"technical and educational"},
    {"topic":"The difference between being busy and increasing throughput.","voice":"productivity and technical"},
    {"topic":"Why every successful person unknowingly runs experiments.","voice":"scientific and educational"},
    {"topic":"The science of compounding is bigger than money.","voice":"analytical and inspiring"},
    {"topic":"A product manager taught me the danger of feature creep in life.","voice":"technical and reflective"},
    {"topic":"The paradox of efficiency: why faster isn't always better.","voice":"systems-thinking and educational"},
    {"topic":"A simple probability lesson can improve almost every decision you make.","voice":"mathematical and practical"},
    {"topic":"The internet runs on trust. So do successful teams.","voice":"technical and insightful"},
    {"topic":"What distributed systems can teach us about resilience.","voice":"technical and inspiring"},
    {"topic":"The bug wasn't in the code. It was in our assumptions.","voice":"critical-thinking and storytelling"},
    {"topic":"Why successful people think in second-order effects.","voice":"strategic and educational"},
    {"topic":"The most valuable skill isn't learning. It's updating your beliefs.","voice":"psychology and analytical"},
    {"topic":"An AI model exposed a flaw in human decision-making.","voice":"technology and thought-provoking"},
    {"topic":"The architecture of a great life looks surprisingly similar to great software.","voice":"technical and philosophical"},
    {"topic":"Most failures are latency problems, not intelligence problems.","voice":"technical and motivational"},
    {"topic":"The startup metric that quietly predicts survival.","voice":"business and educational"},
    {"topic":"What game theory reveals about everyday relationships.","voice":"educational and insightful"},
    {"topic":"A physics principle explains why some people accelerate faster than others.","voice":"scientific and motivational"},
    {"topic":"The difference between motion and progress can be measured.","voice":"analytical and inspiring"},
    {"topic":"The engineer's secret: solve the root cause once.","voice":"technical and practical"},
    {"topic":"Why constraints often create better solutions than freedom.","voice":"innovation and educational"},
    {"topic":"The hidden leverage points inside every system.","voice":"systems-thinking and insightful"},
    {"topic":"Most people underestimate exponential growth until it's too late.","voice":"mathematical and thought-provoking"},
    {"topic":"A data scientist explained success using signal and noise.","voice":"technical and educational"},
    {"topic":"The biggest risk isn't failure. It's local optimization.","voice":"strategic and analytical"},
    {"topic":"Why every breakthrough begins as an ugly prototype.","voice":"innovation and inspiring"},
    {"topic":"The feedback loop that separates amateurs from experts.","voice":"educational and practical"},
    {"topic":"The most dangerous assumption in business is that customers think like you.","voice":"business and insightful"},
    {"topic":"A systems engineer taught me why motivation is overrated.","voice":"technical and motivational"}
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



