import subprocess
import sys

def run_script(name):
    print(f"\n🔧 Running: {name}")
    result = subprocess.run([sys.executable, name])
    
    if result.returncode != 0:
        print(f"❌ Error running {name}")
    else:
        print(f"✅ Finished: {name}")


def main():
    print("🚀 Starting daily Nika Visa AI content pipeline...\n")

    # 1. Extract new data from PDFs + URLs
    run_script("extract_internal_data.py")

    # 2. Fetch updated links (only if you use link auto-scraper)
    try:
        run_script("auto_fetch_links.py")
    except Exception:
        print("⚠️ Skipping auto_fetch_links.py (not required).")

    # 3. Generate a daily Telegram post
    run_script("auto_poster.py")

    print("\n🎉 All tasks completed for today.")


if __name__ == "__main__":
    main()
