from flask import Flask, send_from_directory, request, jsonify
import os
import time
import requests
from leya_secrets import GEMINI_API_KEY

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def home():
    return send_from_directory(
        BASE_DIR,
        "leya_interface_v04-5_face_detection.html"
    )


@app.route("/face-test")
def face_test():
    return send_from_directory(
        BASE_DIR,
        "leya_face_detection_test.html"
    )
    

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/interactions"

        max_attempts = 3

        for attempt in range(max_attempts):
            response = requests.post(
                url,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gemini-3.8-flash",
                    "input": message
                },
                timeout=30
            )

            # Retry temporary server errors
            if response.status_code in (500, 502, 503, 504):
                try:
                    error_details = response.json()
                except ValueError:
                    error_details = response.text

                print("Gemini status:", response.status_code)
                print("Gemini details:", error_details)

                if attempt < max_attempts - 1:
                    wait_seconds = 2 ** (attempt + 1)
                    print(f"Retrying in {wait_seconds} seconds...")
                    time.sleep(wait_seconds)
                    continue

            break

        if response.status_code != 200:
            print("Gemini API status:", response.status_code)
            
            try:
                print("Gemini API error:", response.json())
            except ValueError:
                print("Gemini response:", response.text)

            return jsonify({
                "error": f"Gemini returned error {response.status_code}. Please try again later."
            }), 502

        reply = next(
            step["content"]
            for step in reversed(result["steps"])
            if step.get("type") == "model_output"
            and isinstance(step.get("content"), str)
        )

        return jsonify({"reply": reply})

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Gemini took too long to respond. Please try again."
        }), 504

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "Couldn't connect to Gemini. Check your internet connection."
        }), 502

    except (KeyError, IndexError, TypeError):
        return jsonify({
            "error": "Gemini returned an unexpected response. Check the server console."
        }), 502


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )