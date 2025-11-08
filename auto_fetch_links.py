import requests, json, os
from bs4 import BeautifulSoup
from datetime import datetime

# Path where we save new URLs
LINKS_FILE = "internal_knowledge/auto_links.txt"

# Example immigration / study RSS feeds
FEEDS = [
    "https://www.schengenvisainfo.com/news/feed/",
    "https://www.study.eu/rss",
    "https://www.gov.uk/government/announcements.atom"
]

def fetch_latest_links():
    all_links = set()
    for url in FEEDS:
        print(f"🌐 Fetching from {url}")
        try:
            html = requests.get(url, timeout=10).text
            soup = BeautifulSoup(html, "xml")
            for tag in soup.find_all(["link", "id"]):
                if tag.text.startswith("http"):
                    all_links.add(tag.text.strip())
        except Exception as e:
            print(f"⚠️ Failed to fetch from {url}: {e}")

    # Append new links to the auto_links.txt
    existing = set()
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r") as f:
            existing = set(line.strip() for line in f if line.strip())

    new_links = list(all_links - existing)
    if new_links:
        with open(LINKS_FILE, "a") as f:
            for link in new_links:
                f.write(link + "\n")
        print(f"✅ Added {len(new_links)} new links.")
    else:
        print("ℹ️ No new links found today.")

if __name__ == "__main__":
    fetch_latest_links()
