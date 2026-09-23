import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
if not key:
    print("ERROR: OPENROUTER_API_KEY is not configured")
    raise SystemExit(1)

image_path = "static/uploads/80aae07a34c548428d970eb4f48b7c84.jpg"

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "nex-agi/nex-n2.5-mini:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Look at this image. In one short sentence, describe the main object."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
    },
    timeout=60,
)

print("HTTP status:", response.status_code)

try:
    data = response.json()

    if response.ok:
        print("Model used:", data.get("model"))
        print("Provider:", data.get("provider"))
        print("AI response:")
        print(data["choices"][0]["message"]["content"])
    else:
        print("OpenRouter error:")
        print(data)

except ValueError:
    print("Non-JSON response:")
    print(response.text)