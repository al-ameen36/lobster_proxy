import os
import requests

MODEL = "gemini/gemini-2.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def main():
    res = requests.post(
        url="http://localhost:8000/v1/chat/completions",
        headers={"Content-Type": "application/json", "api_key": GEMINI_API_KEY},
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "I want to pay $500 to Vendor X."}
            ],
        },
    )

    print(res.json())


if __name__ == "__main__":
    main()
