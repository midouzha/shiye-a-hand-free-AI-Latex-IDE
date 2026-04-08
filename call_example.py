import os

from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY", "").strip()
base_url = os.getenv("OPENAI_BASE_URL", "https://api.chatanywhere.tech/v1").strip()

if not api_key:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)