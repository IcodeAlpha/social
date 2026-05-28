# 🤖 AI Social Media Bot

Automated social media posting powered by **Gemini AI** (captions) + **DALL·E 3** (images).

## Stack

| Layer | Tool |
|---|---|
| Caption AI | Google Gemini 1.5 Flash |
| Image AI | OpenAI DALL·E 3 |
| Instagram | Meta Graph API v19 |
| X (Twitter) | Twitter API v2 + Tweepy |
| LinkedIn | LinkedIn UGC API v2 |
| Scheduler | `schedule` library |

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
# Edit .env and fill in all values
```

Load env vars before running:
```bash
export $(cat .env | xargs)
# or use python-dotenv (add `load_dotenv()` to any script)
```

### 3. API accounts you need

| Service | Where to get it |
|---|---|
| Gemini API key | https://aistudio.google.com/app/apikey |
| OpenAI API key | https://platform.openai.com/api-keys |
| Meta / Instagram | https://developers.facebook.com → create App → Instagram Basic Display |
| Twitter/X | https://developer.twitter.com → Basic plan (~$100/mo required for posting) |
| LinkedIn | https://developer.linkedin.com → create App → request `w_member_social` |
| Imgur (optional) | https://api.imgur.com/oauth2/addclient (anonymous upload, free) |

---

## Usage

### Generate one post right now
```bash
python post_generator.py "The rise of AI agents in 2025" \
  --platforms instagram twitter linkedin \
  --voice "visionary and approachable"
```

### Run a specific calendar entry immediately
```bash
python scheduler.py --run-now 1
```

### Preview the schedule (no posting)
```bash
python scheduler.py --dry-run
```

### Start the full automation loop
```bash
python scheduler.py
```

---

## Project Structure

```
social_ai_bot/
├── post_generator.py        # Phase 1: Gemini + DALL·E 3 core agent
├── scheduler.py             # Phase 3: Automation runner
├── content_calendar.json    # Your posting schedule
├── requirements.txt
├── .env.example
├── connectors/
│   ├── instagram_poster.py  # Meta Graph API
│   ├── twitter_poster.py    # Twitter API v2
│   └── linkedin_poster.py   # LinkedIn API v2
├── utils/
│   └── logger.py
├── output/                  # Generated images + post packages saved here
└── logs/
    └── bot.log
```

---

## Content Calendar Format

Edit `content_calendar.json` to customise your schedule:

```json
{
  "id": 1,
  "topic": "Your post topic or theme",
  "platforms": ["instagram", "twitter", "linkedin"],
  "brand_voice": "professional yet approachable",
  "extra_instructions": "Any specific guidance for Gemini",
  "scheduled_time": "09:00",
  "days": ["monday", "thursday"]
}
```

---

## Roadmap

- [x] Phase 1 — Core agent (Gemini + DALL·E 3)
- [x] Phase 2 — Platform connectors (Instagram, Twitter, LinkedIn)
- [x] Phase 3 — Scheduler + content calendar
- [ ] Phase 4 — Telegram/email notifications
- [ ] Phase 4 — Preview dashboard
- [ ] Phase 4 — Brand voice fine-tuning UI
