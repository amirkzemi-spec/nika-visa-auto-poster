import json, random, requests, os, time, schedule
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv   # ✅ NEW

# ------------------------------
# 🔐 Configuration
# ------------------------------
load_dotenv()  # ✅ Load .env file automatically

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL = "@nikavisa"  # or numeric ID if private
POST_FILE = "internal_posts.json"
LOG_FILE = "posted_log.json"

# ✅ create client *after* loading environment
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------
# 🧠 Utilities
# ------------------------------
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def pick_unposted_item(posts, log):
    unposted = [p for p in posts if p["source"] not in log]
    return random.choice(unposted) if unposted else None

def rephrase_and_tag(post):
    try:
        # 🎯 Choose one random footer for each post
        footer_options = [
            "📞 برای اطلاعات بیشتر با نیکا ویزا تماس بگیرید: 09910777743",
            "🤖 اگر سوالی درباره مهاجرت دارید، از ربات هوش مصنوعی ما در @applypal_bot بپرسید",
            "📅 برای رزرو وقت مشاوره، به ادمین پیام دهید: @nikavisa_admin"
        ]
        footer = random.choice(footer_options)

        prompt = f"""
        متن زیر مربوط به تحصیل یا مهاجرت است. آن را به فارسی روان و جذاب خلاصه و بازنویسی کن.
        در ابتدای پیام، یک تیتر کوتاه و توصیفی قرار بده که باید درون تگ HTML <b> </b> باشد (برای بولد شدن در تلگرام).
        در انتهای پیام سه هشتگ مرتبط اضافه کن (به فارسی).
        سپس جمله زیر را به عنوان امضای انتهایی اضافه کن:
        {footer}

        عنوان: {post['title']}
        متن: {post['content']}
        """

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.choices[0].message.content.strip()

        # Ensure Telegram-safe HTML formatting
        if not text.startswith("<b>"):
            text = f"<b>{post['title']}</b>\n\n{text}"

        return text

    except Exception as e:
        print(f"⚠️ GPT rephrase failed: {e}")
        # 🔁 fallback with random footer
        fallback_footer = random.choice([
            "📞 برای اطلاعات بیشتر با نیکا ویزا تماس بگیرید: 09910777743",
            "🤖 اگر سوالی درباره مهاجرت دارید، از ربات ما در @applypal_bot بپرسید",
            "📅 برای رزرو وقت مشاوره به @nikavisa_admin پیام دهید"
        ])
        return f"<b>{post['title']}</b>\n\n{post['content']}\n\n{fallback_footer}"


def post_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML"}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        print(f"✅ Posted successfully at {datetime.now()}")
    else:
        print(f"❌ Telegram error: {r.text}")

# ------------------------------
# 🚀 Main Posting Logic
# ------------------------------
def post_one_item():
    posts = load_json(POST_FILE)
    log = load_json(LOG_FILE)

    post = pick_unposted_item(posts, log)
    if not post:
        print("⚠️ No new posts available.")
        return

    text = rephrase_and_tag(post)
    post_to_telegram(text)
    log.append(post["source"])
    save_json(log, LOG_FILE)

# ------------------------------
# ⏰ Scheduler
# ------------------------------
def run_scheduler():
    schedule.every().day.at("10:00").do(post_one_item)  # change time if needed
    print("🕒 Auto-poster running... waiting for schedule.")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ------------------------------
# 🏁 Entry point
# ------------------------------
if __name__ == "__main__":
    post_one_item()  # test now
    # run_scheduler()  # uncomment for daily automation
