import os
import requests
import json

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

data = {
    "model": "gemini-2.5-flash",
    "messages": messages,
    "stream": True
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

try:
    res = requests.post(url, headers=headers, json=data)
    print("STATUS:", res.status_code)
    print("TEXT:", res.text)
except Exception as e:
    print(e)
