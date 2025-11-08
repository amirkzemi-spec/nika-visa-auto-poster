import os, time

print("⏳ [1/3] Fetching latest links...")
os.system("python auto_fetch_links.py")

print("⏳ [2/3] Extracting content from all sources...")
os.system("python extract_internal_data.py")

print("⏳ [3/3] Posting to Telegram...")
os.system("python auto_poster.py")

print("✅ All done!")
