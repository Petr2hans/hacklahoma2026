import json
import urllib.request
import urllib.parse

from config import GEMINI_API_KEY, GEMINI_URL

def call_gemini(prompt: str, temperature: float = 0.2, timeout_s: int = 30) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    url = f"{GEMINI_URL}?key={urllib.parse.quote(GEMINI_API_KEY)}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        response_data = json.loads(resp.read().decode("utf-8"))

    try:
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise RuntimeError(f"Unexpected Gemini response format: {response_data}") from e