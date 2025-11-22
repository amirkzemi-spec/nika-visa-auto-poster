import os
import json
import re
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------------
# Select folder dynamically
# -----------------------------------------------
if len(sys.argv) > 1:
    INTERNAL_DIR = sys.argv[1]
else:
    INTERNAL_DIR = "internal_knowledge"

OUTPUT_FILE = "internal_posts.json"

print("USING KNOWLEDGE FOLDER:", INTERNAL_DIR)

# ------------------------------------------------------------
# JSON Helpers
# ------------------------------------------------------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# HARD CHUNKING – fallback for giant files
# ------------------------------------------------------------
def chunk_text(text, max_words=120):
    """
    If a block is too large, we split it into pure word slices.
    This ensures GPT never receives overly large inputs.

    Used ONLY when smart_split() fails or block still too large.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_words):
        slice_ = " ".join(words[i:i+max_words])
        chunks.append(slice_)

    return chunks


# ------------------------------------------------------------
# SMART CHUNKING – split by headings (###)
# ------------------------------------------------------------
def smart_split(text, max_words=120):
    """
    1. Split by headings starting with ###
    2. If a block exceeds max_words → re-split via chunk_text()
    """
    blocks = re.split(r"###\s+", text)
    blocks = [b.strip() for b in blocks if b.strip()]

    clean_blocks = []

    for b in blocks:
        lines = b.splitlines()
        if len(lines) == 0:
            continue

        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        # too small → skip noise
        if len(body) < 40:
            continue

        # If too large, chunk further
        if len(body.split()) > max_words:
            subchunks = chunk_text(body, max_words=max_words)
            for idx, sc in enumerate(subchunks):
                clean_blocks.append(f"{title} (Part {idx+1})\n{sc}")
        else:
            clean_blocks.append(f"{title}\n{body}")

    if len(clean_blocks) == 0:
        return chunk_text(text)  # fallback to word slicing

    return clean_blocks[:30]   # global safety limit


# ------------------------------------------------------------
# Classification via GPT
# ------------------------------------------------------------
def classify_block(block):
    prompt = f"""
You are an immigration content classifier.

Return STRICT JSON with keys:
{{
  "category": "...",
  "title": "...",
  "summary": "...",
  "confidence": 0.0
}}

RULES:
- NEVER return a list
- NEVER add explanation
- Title must reference ONE country or ONE topic only
- Category must be one of:
    "startup_visa", "student_visa", "work_permit",
    "immigration_update", "scholarship", "general"

TEXT:
{block}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            timeout=12
        )
        raw = response.output_text

        # Try parse JSON
        try:
            parsed = json.loads(raw)
        except:
            if raw.strip().startswith("["):
                try:
                    parsed = json.loads(raw)[0]
                except:
                    return None
            else:
                return None

        if not isinstance(parsed, dict):
            return None

        return {
            "category": parsed.get("category", "general"),
            "title": parsed.get("title", "Untitled"),
            "summary": parsed.get("summary", ""),
            "confidence": parsed.get("confidence", 0.0)
        }

    except Exception as e:
        print("Classification error:", e)
        return None


# ------------------------------------------------------------
# FILE PROCESSING
# ------------------------------------------------------------
def process_file(filepath):
    print(f"\n📄 Processing file: {filepath}")
    text = open(filepath, "r", encoding="utf-8").read()

    blocks = smart_split(text, max_words=120)
    print(f"  → Generated {len(blocks)} blocks")

    filename = os.path.basename(filepath)
    posts = []

    for idx, block in enumerate(blocks):
        print(f"    • Classifying block {idx+1}/{len(blocks)}...")
        classification = classify_block(block)

        if not classification:
            print("      ⚠ Skipped (invalid JSON or GPT failure)")
            continue

        # Force startup visa override
        if "startup" in filename.lower():
            classification["category"] = "startup_visa"

        post = {
            "title": classification["title"],
            "category": classification["category"],
            "content": classification["summary"],
            "source": filename
        }

        posts.append(post)

    print(f"  → Finished {filename}. Extracted {len(posts)} posts.")
    return posts


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    existing = load_json(OUTPUT_FILE, default=[])
    new_posts = []

    files = sorted(os.listdir(INTERNAL_DIR))
    text_files = [f for f in files if f.lower().endswith((".txt", ".md", ".rtf"))]

    print(f"Found {len(text_files)} files in internal_knowledge/")

    for f in text_files:
        full_path = os.path.join(INTERNAL_DIR, f)
        extracted = process_file(full_path)
        new_posts.extend(extracted)

    combined = existing + new_posts
    save_json(OUTPUT_FILE, combined)

    print(f"\n✅ Added {len(new_posts)} new posts.")
    print(f"📦 Total posts stored: {len(combined)}")


if __name__ == "__main__":
    main()
