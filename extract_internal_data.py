import os, json, tempfile, pytesseract, requests, mimetypes
import fitz  # PyMuPDF
import docx
from PIL import Image
from openai import OpenAI
from tqdm import tqdm
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ----------------------------
# 🔐 Configuration
# ----------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INPUT_DIR = "internal_knowledge"
OUTPUT_FILE = "internal_posts.json"
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# 📘 Helper functions
# ----------------------------
def extract_text_from_pdf(path):
    text = ""
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text("text") + "\n"
    return text.strip()

def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def extract_text_from_image(path):
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img, lang="eng+fas")
    except Exception as e:
        print(f"❌ OCR failed for {path}: {e}")
        return ""

def transcribe_audio(path):
    try:
        with open(path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f
            )
        return transcript.text.strip()
    except Exception as e:
        print(f"❌ Whisper transcription failed for {path}: {e}")
        return ""

def clean_text(txt):
    txt = txt.replace("\n", " ").replace("  ", " ").strip()
    return txt[:2000] + "..." if len(txt) > 2000 else txt

# ----------------------------
# 🚀 Main extraction logic
# ----------------------------
def main():
    posts = []

    for root, _, files in os.walk(INPUT_DIR):
        for filename in tqdm(files, desc="Extracting"):
            path = os.path.join(root, filename)
            ext = filename.lower().split(".")[-1]
            text = ""

            try:
                if ext == "pdf":
                    text = extract_text_from_pdf(path)
                elif ext == "docx":
                    text = extract_text_from_docx(path)
                elif ext in ["jpg", "jpeg", "png", "bmp"]:
                    text = extract_text_from_image(path)
                elif ext in ["mp3", "wav", "m4a"]:
                    text = transcribe_audio(path)
                elif ext == "txt":
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()

                    if "http" in content:  # links (YouTube or news)
                        urls = [u.strip() for u in content.splitlines() if u.startswith("http")]
                        for url in urls:
                            print(f"🌐 Fetching {url}")
                            try:
                                html = requests.get(url, timeout=10).text
                                soup = BeautifulSoup(html, "html.parser")
                                paragraphs = " ".join([p.get_text() for p in soup.find_all("p")])
                                text = clean_text(paragraphs)

                                # Summarize YouTube or article page
                                prompt = f"Summarize this webpage in Persian, short and suitable for a Telegram post:\n{text}"
                                resp = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[{"role": "user", "content": prompt}]
                                )
                                summary = resp.choices[0].message.content.strip()

                                posts.append({
                                    "source": url,
                                    "category": "External Link",
                                    "title": soup.title.string[:80] if soup.title else "Web Page",
                                    "content": summary
                                })
                            except Exception as e:
                                print(f"❌ Failed to fetch {url}: {e}")
                        continue
                    else:
                        text = content
                else:
                    if mimetypes.guess_type(path)[0] and "text" in mimetypes.guess_type(path)[0]:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()

            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")

            if text.strip():
                posts.append({
                    "source": filename,
                    "category": "General",
                    "title": os.path.splitext(filename)[0].replace("_", " ").title(),
                    "content": clean_text(text)
                })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Extraction complete! {len(posts)} posts saved to {OUTPUT_FILE}")

# ----------------------------
# 🏁 Run
# ----------------------------
if __name__ == "__main__":
    main()
