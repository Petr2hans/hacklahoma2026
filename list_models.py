from dotenv import load_dotenv
load_dotenv()

import os
import json
import urllib.request
import urllib.parse

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={urllib.parse.quote(GEMINI_API_KEY)}"

req = urllib.request.Request(url, headers={"Content-Type": "application/json"})

with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print(json.dumps(data, indent=2))