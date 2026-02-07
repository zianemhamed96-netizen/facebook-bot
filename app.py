from flask import Flask, request
import requests
import re
import os

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_token_123")

GRAPH_URL = "https://graph.facebook.com/v16.0/me/messages"


# ---------- إرسال رسالة نصية ----------
def send_text_message(recipient_id, message_text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    try:
        r = requests.post(GRAPH_URL, params=params, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print("Send text error:", e)


# ---------- إرسال صورة ----------
def send_image_message(recipient_id, image_url):
    params = {"access_token": PAGE_ACCESS_TOKEN}
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
    try:
        r = requests.post(GRAPH_URL, params=params, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print("Send image error:", e)


# ---------- حالة الكتابة ----------
def send_sender_action(recipient_id, action):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    try:
        requests.post(GRAPH_URL, params=params, json=payload, timeout=5)
    except:
        pass


# ---------- استخراج بيانات المنشور ----------
def extract_post_data(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = requests.get(url, headers=headers, timeout=10)

        image = re.search(r'property="og:image" content="([^"]+)"', r.text)
        title = re.search(r'property="og:title" content="([^"]+)"', r.text)
        desc = re.search(r'property="og:description" content="([^"]+)"', r.text)

        return {
            "title": title.group(1) if title else "منشور فيسبوك",
            "description": desc.group(1) if desc else "",
            "image": image.group(1) if image else None
        }
    except Exception as e:
        print("Extract error:", e)
        return None


# ---------- الصفحة الرئيسية ----------
@app.route("/")
def home():
    return "✅ البوت يعمل"


# ---------- التحقق من Webhook ----------
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge")
    return "Forbidden", 403


# ---------- استقبال الرسائل ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("object") != "page":
        return "OK", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]

            if event.get("message") and event["message"].get("text"):
                text = event["message"]["text"]

                send_sender_action(sender_id, "typing_on")

                # استخراج أي رابط من النص
                link_match = re.search(r"(https?://\S+)", text)

                if link_match and ("facebook.com" in link_match.group(1) or "fb.com" in link_match.group(1)):
                    handle_link(sender_id, link_match.group(1))
                else:
                    send_text_message(sender_id, "📎 أرسل رابط منشور فيسبوك")

                send_sender_action(sender_id, "typing_off")

    return "OK", 200


# ---------- معالجة الرابط ----------
def handle_link(sender_id, url):
    send_text_message(sender_id, "⏳ جاري جلب المنشور...")

    data = extract_post_data(url)
    if not data:
        send_text_message(sender_id, "❌ لم أستطع جلب المنشور")
        return

    msg = data["title"]
    if data["description"]:
        msg += "\n\n" + data["description"]

    send_text_message(sender_id, msg)

    if data["image"]:
        send_image_message(sender_id, data["image"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
