import os
import json
import datetime
import requests
import re
from openai import OpenAI
from dotenv import load_dotenv

# -------------------------------------------------
# Load environment
# -------------------------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

POSTS_FILE = "internal_posts.json"
POSTING_PLAN_FILE = "posting_plan.json"
POSTED_LOG_FILE = "posted_log.json"


# -------------------------------------------------
# JSON Helpers
# -------------------------------------------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -------------------------------------------------
# Telegram API
# -------------------------------------------------
def send_text_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)


def send_poll(question, options):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": CHANNEL_ID,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": True,
    }
    requests.post(url, data=payload)


# -------------------------------------------------
# Formatting helper (Markdown → Telegram HTML)
# -------------------------------------------------
def md_to_html(text):
    if not text:
        return text

    # **bold** → <b>bold</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    # Remove accidental markdown artifacts
    text = text.replace("__", "")
    text = text.replace("```", "")

    return text.strip()

# -------------------------------------------------
# Category Rules
# -------------------------------------------------
def category_rules(category):
    if category == "startup_visa":
        return """
Rewrite as a HIGH-VALUE startup visa guide.

Rules:
- Start with a <b>bold title</b>
- Provide 4–7 SPECIFIC bullet points:
    • Eligibility
    • Minimum requirements
    • Documents
    • Processing time
    • Benefits
    • Who qualifies / who doesn’t
- Write in direct, professional Persian
- NO generic intros like “در این مطلب”
- Add 2 relevant hashtags at the end
"""

    if category == "student_visa":
        return """
Rewrite as a clear student visa guide.

Rules:
- Start with a <b>bold title</b>
- Provide 4–6 practical bullet points about:
    • زبان، تمکن، مدارک
    • زمان‌بندی اپلای
    • شهریه و هزینه زندگی
    • نکات مهم سفارت
- No storytelling
- No fluff
- Add 2 student visa hashtags
"""

    if category == "scholarship":
        return """
Rewrite as a high-quality PhD scholarship guide.

Rules:
- Start with a <b>bold title</b>
- Provide structured info:
    • Funding amount / benefits
    • Eligibility
    • Supervisor requirement
    • Deadlines
    • Notes for Iranian applicants
- Add 1–2 scholarship hashtags
"""

    if category == "immigration_update":
        return """
Rewrite as an immigration update.

Rules:
- Start with <b>bold title of the update</b>
- Add:
    • What changed
    • Who is affected
    • Why it matters
    • What applicants should do next
- Avoid generic intros
- Add 1–2 relevant hashtags
"""

    if category == "work_permit":
        return """
Rewrite as a professional work permit / FIP visa guide.

Rules:
- Start with a <b>bold title</b>
- Provide:
    • Income requirements
    • Job contract rules
    • Timeline
    • Legal notes
    • Common mistakes
- Add 1–2 hashtags
"""

    if category == "general":
        return """
Rewrite as a motivational post.

Rules:
- Start with a <b>bold insight</b>
- Keep it SHORT and powerful
- Add a single actionable takeaway
- Add 1 motivational hashtag
"""

    return "Rewrite clearly and concisely."


# -------------------------------------------------
# GPT rewriting
# -------------------------------------------------
def rewrite_content(raw_text, category="general"):
    rules = category_rules(category)

    prompt = f"""
{rules}

TEXT:
{raw_text}

Rewrite now according to all rules.
"""

    try:
        completion = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )
        return completion.output_text.strip()

    except Exception as e:
        print("Rewrite error:", e)
        return raw_text

# -------------------------------------------------
# GPT rewriting
# -------------------------------------------------

# -------------------------------------------------
# CTA (Add this right after rewrite_content)
# -------------------------------------------------
CTA_TEXT = (
    "\n\n"
    "برای دریافت مشاوره هوشمند و بررسی فوری شرایطت، "
    "به وب‌سایت مشاور هوشمند نیکاوایزا مراجعه کن:\n"
    "<a href=\"https://advisor.nikavisa.com\">advisor.nikavisa.com</a>"
)

# -------------------------------------------------
# Select category of today
# -------------------------------------------------
def get_today_category():
    plan = load_json(POSTING_PLAN_FILE, {})
    today = datetime.datetime.now().strftime("%A")
    return plan.get(today)


# -------------------------------------------------
# Select next unused content item
# -------------------------------------------------
def select_item(category):
    posts = load_json(POSTS_FILE, default=[])
    posted = load_json(POSTED_LOG_FILE, default=[])

    candidates = [
        p for p in posts
        if p["category"] == category and p["title"] not in posted
    ]

    if not candidates:
        return None

    return candidates[0]


# -------------------------------------------------
# AUTO POSTING WORKFLOW
# -------------------------------------------------
def main():

    # Debug
    print("BOT:", BOT_TOKEN[:8] + "...")
    print("CHANNEL:", CHANNEL_ID)
    print("OpenAI:", OPENAI_API_KEY[:10] + "...")
    today = datetime.datetime.now().strftime("%A")
    print("Today:", today)

    category = get_today_category()
    print("Category:", category)

    if category == "poll":
        send_poll(
            "کدام موضوع را دوست دارید بیشتر درباره‌اش پست بگذاریم؟",
            ["ویزای تحصیلی", "ویزای کاری", "ویزای استارتاپی", "بورسیه‌ها"]
        )
        return

    item = select_item(category)

    if not item:
        send_text_message(
            f"<b>هیچ محتوایی برای {category} یافت نشد.</b>\n\n"
            "لطفاً فایل‌های internal_knowledge را بروزرسانی کنید."
        )
        return

    # Rewrite content
    rewritten = rewrite_content(item["content"], category=item["category"])
    final_text = md_to_html(rewritten.strip()) + CTA_TEXT

    if not final_text.strip():
        final_text = "<b>خطا در پردازش محتوا</b>"

    send_text_message(final_text)

    # Log item
    posted = load_json(POSTED_LOG_FILE, default=[])
    posted.append(item["title"])
    save_json(POSTED_LOG_FILE, posted)

    print("Posted:", item["title"])


if __name__ == "__main__":
    main()
