import os
import json
import datetime
import requests
import re
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv(dotenv_path=".env", override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# JSON Files
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
    return requests.post(url, json=payload)

def send_poll(question, options):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": CHANNEL_ID,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": True,
    }
    return requests.post(url, data=payload)

def notify_admin(message):
    if not ADMIN_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_ID,
        "text": f"[AutoPoster Alert]\n{message}",
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

# -------------------------------------------------
# Category Normalization (Intelligent)
# -------------------------------------------------
CATEGORY_MAP = {
    "startup": "Startup Visa",
    "استارتاپ": "Startup Visa",
    "کارآفرینی": "Startup Visa",
    "innovation": "Startup Visa",

    "student": "Student Visa",
    "study": "Student Visa",
    "اقامت تحصیلی": "Student Visa",

    "immigration": "Immigration Updates",
    "update": "Immigration Updates",
    "news": "Immigration Updates",

    "work": "Work Permit",
    "permit": "Work Permit",
    "employment": "Work Permit",
    "post-study": "Work Permit",

    "general": "General",
    "motivation": "General",
    "external": "General"
}

def normalize_category(cat, title, content):
    full_text = f"{cat} {title} {content}".lower()
    for key, mapped in CATEGORY_MAP.items():
        if key in full_text:
            return mapped
    return "General"

# -------------------------------------------------
# Markdown → Telegram HTML
# -------------------------------------------------
def md_to_html(text):
    if not text:
        return text
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = text.replace("__", "")
    text = text.replace("```", "")
    return text.strip()

# -------------------------------------------------
# Category-specific rewriting rules (UPGRADED)
# -------------------------------------------------
def category_rules(category):
    base = """
- متن را کاملاً به زبان فارسی و به شکل حرفه‌ای بازنویسی کن.
- لحن: صریح، قدرتمند، جذاب، با نکات عملی ویژه متقاضیان ایرانی.
- از کلی‌گویی و عبارت‌های عمومی پرهیز کن.
- یک عنوان جذاب و کاملاً بولد در ابتدای متن بیاور.
- ساختار متن باید کوتاه، لایه‌لایه و کاربردی باشد.
"""

    if category == "Startup Visa":
        return base + """
- توضیح بده این نوع ویزا دقیقاً برای چه نوع استارتاپ‌ها و کارآفرینانی مناسب است (نوآوری، مدل کسب‌وکار، ارزش افزوده).
- مراحل اصلی را برای کشور مقصد «به صورت کلی اما دقیق» مرحله‌به‌مرحله فهرست کن:  
  ایده → اعتبارسنجی → بیزنس‌پلن → شتاب‌دهنده/سرمایه‌گذار → Letter of Support یا Approval → ارسال پرونده.
- اگر متن درباره کشور خاصی است (هلند، فرانسه، پرتغال، کانادا، استونی، فنلاند...) نکات مهم و الزامات همان کشور را اضافه کن.
- اشتباهات رایج متقاضیان ایرانی را دقیق و کاربردی بیان کن.
- یک «نکته طلایی» ذکر کن که کمتر کسی می‌داند و واقعاً ارزش‌افزوده دارد.
- در پایان ۲ هشتگ تخصصی مناسب بنویس (#ویزای_استارتاپی #StartupVisa).
"""

    if category == "Student Visa":
        return base + """
- زبان، تمکن مالی، مدارک، SOP و زمان‌بندی اپلای را واضح و فشرده توضیح بده.
- هزینه‌ها و شرایط واقعی سال جاری را بنویس.
- مراحل از اپلای تا ویزا را مرحله‌به‌مرحله فهرست کن.
- اشتباهات رایج دانشجویان ایرانی را ذکر کن.
- ۲ هشتگ دانشجویی اضافه کن.
"""

    if category == "Immigration Updates":
        return base + """
- تغییر جدید را با شفافیت کامل توضیح بده.
- بگو این تغییر چه گروه‌هایی را تحت‌تأثیر قرار می‌دهد.
- دلیل اهمیت این تغییر را ذکر کن.
- توصیه کن متقاضی الان باید چه کاری انجام دهد.
"""

    if category == "Work Permit":
        return base + """
- توضیح بده این نوع ویزا برای چه افرادی مناسب است.
- حداقل درآمد، نوع قرارداد، شرایط تمدید و نکات حقوقی را بیان کن.
- برای متقاضیان ایرانی نکات مهم رد شدن و اشتباهات رایج را اضافه کن.
"""

    return base

# -------------------------------------------------
# GPT Rewriting (UPGRADED)
# -------------------------------------------------
def rewrite_content(raw_text, category="General"):
    rules = category_rules(category)

    prompt = f"""
{rules}

متن زیر فقط یک منبع اطلاعاتی اولیه است.  
اما خروجی باید یک پست **کاملاً جدید، مفید، جذاب و حرفه‌ای** باشد:

«{raw_text}»

اکنون متن را بازنویسی کن:
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )
        return response.output_text.strip()

    except Exception as e:
        notify_admin(f"Rewrite failed: {e}")
        return raw_text

# -------------------------------------------------
# CTA
# -------------------------------------------------
CTA_TEXT = (
    "\n\n"
    "برای دریافت مشاوره هوشمند و بررسی فوری شرایطت، "
    "به مشاور هوشمند نیکاوایزا مراجعه کن:\n"
    "<a href=\"https://advisor.nikavisa.com\">advisor.nikavisa.com</a>"
)

# -------------------------------------------------
# Category of today
# -------------------------------------------------
def get_today_category():
    plan = load_json(POSTING_PLAN_FILE, {})
    today = datetime.datetime.now().strftime("%A")
    return plan.get(today)

# -------------------------------------------------
# Select item using normalized category
# -------------------------------------------------
def select_item(target_category):
    posts = load_json(POSTS_FILE, default=[])
    posted = load_json(POSTED_LOG_FILE, default=[])

    candidates = []

    for p in posts:
        normalized = normalize_category(
            p.get("category", ""),
            p.get("title", ""),
            p.get("content", "")
        )
        if normalized == target_category and p["title"] not in posted:
            candidates.append(p)

    if not candidates:
        return None

    return candidates[0]

# -------------------------------------------------
# MAIN AUTO POSTER
# -------------------------------------------------
def main():
    print("BOT:", BOT_TOKEN[:10] + "...")
    print("CHANNEL:", CHANNEL_ID)
    print("OpenAI:", OPENAI_API_KEY[:10] + "...")
    print("Today:", datetime.datetime.now().strftime("%A"))

    category = get_today_category()
    print("Category:", category)

    # Case: Poll Day
    if category == "poll":
        send_poll(
            "کدام موضوع را دوست دارید بیشتر درباره‌اش پست بگذاریم؟",
            ["ویزای تحصیلی", "ویزای کاری", "ویزای استارتاپی", "بورسیه‌ها"]
        )
        return

    # Get content
    item = select_item(category)

    if not item:
        msg = f"<b>هیچ محتوایی برای {category} یافت نشد.</b>"
        send_text_message(msg)
        notify_admin(msg)
        return

    # Rewrite
    rewritten = rewrite_content(item["content"], category=category)
    final_text = md_to_html(rewritten) + CTA_TEXT

    # Post
    send_text_message(final_text)

    # Log
    posted = load_json(POSTED_LOG_FILE, default=[])
    posted.append(item["title"])
    save_json(POSTED_LOG_FILE, posted)

    print("Posted:", item["title"])

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":
    main()
