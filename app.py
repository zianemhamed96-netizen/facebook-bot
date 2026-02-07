from flask import Flask, request
import requests
import re
import os

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

GRAPH_URL = "https://graph.facebook.com/v16.0/me/messages"


def send_text_message(recipient_id, message_text):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    return requests.post(
        GRAPH_URL,
        params={"access_token": PAGE_ACCESS_TOKEN},
        json=payload
    ).json()


def send_image_message(recipient_id, image_url):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True
                }
            }
        }
    }
    return requests.post(
        GRAPH_URL,
        params={"access_token": PAGE_ACCESS_TOKEN},
        json=payload
    ).json()


def send_sender_action(recipient_id, action):
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    requests.post(
        GRAPH_URL,
        params={"access_token": PAGE_ACCESS_TOKEN},
        json=payload
    )


def extract_post_data(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)

        image = re.search(
            r'property="og:image"\s+content="([^"]+)"', response.text)
        title = re.search(
            r'property="og:title"\s+content="([^"]+)"', response.text)
        desc = re.search(
            r'property="og:description"\s+content="([^"]+)"', response.text)

        return {
            "title": title.group(1) if title else "منشور فيسبوك",
            "description": desc.group(1) if desc else "",
            "image": image.group(1) if image else None
        }
    except:
        return None


@app.route("/")
def home():
    return "البوت يعمل ✅"


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return "فشل", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("object") != "page":
        return "OK", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]

            if "message" in event and "text" in event["message"]:
                text = event["message"]["text"]

                send_sender_action(sender_id, "typing_on")

                if "facebook.com" in text or "fb.com" in text:
                    handle_link(sender_id, text)
                else:
                    send_text_message(
                        sender_id,
                        "📎 أرسل رابط منشور فيسبوك عام"
                    )

                send_sender_action(sender_id, "typing_off")

    return "OK", 200


def handle_link(sender_id, url):
    send_text_message(sender_id, "⏳ جاري جلب المنشور...")

    data = extract_post_data(url)

    if not data:
        send_text_message(sender_id, "❌ لم أستطع الوصول للمنشور")
        return

    message = data["title"]
    if data["description"]:
        message += "\n\n" + data["description"]

    send_text_message(sender_id, message)

    if data["image"]:
        send_image_message(sender_id, data["image"])


if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)