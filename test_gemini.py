import os
import requests

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Hello, are you Gemini?"}],
    "max_tokens": 50
}
try:
    res = requests.post(url, headers=headers, json=data)
    print("Status:", res.status_code)
    print("Text:", res.text)
except Exception as e:
    print(f"Error: {e}")
