from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_token_123")

GRAPH_API_URL = "https://graph.facebook.com/v16.0"

# ======== إرسال الرسائل ========
def send_text_message(recipient_id, message_text):
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    try:
        response = requests.post(url, params=params, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending text: {e}")
        return None

def send_image_message(recipient_id, image_url):
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True}
            }
        }
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    try:
        response = requests.post(url, params=params, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending image: {e}")
        return None

def send_sender_action(recipient_id, action):
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {"recipient": {"id": recipient_id}, "sender_action": action}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    try:
        requests.post(url, params=params, json=payload)
    except:
        pass

# ======== استخراج post_id من الرابط ========
def extract_post_id(fb_url):
    patterns = [
        r'facebook\.com/.+/posts/(\d+)',
        r'facebook\.com/.+/videos/(\d+)',
        r'facebook\.com/permalink\.php\?story_fbid=(\d+)'
    ]
    for pat in patterns:
        match = re.search(pat, fb_url)
        if match:
            return match.group(1)
    return None

# ======== استخدام Graph API لجلب البيانات ========
def get_post_data(post_id):
    url = f"{GRAPH_API_URL}/{post_id}"
    params = {
        "fields": "message,full_picture,permalink_url",
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        return {
            "title": data.get("message", "منشور فيسبوك"),
            "image": data.get("full_picture"),
            "url": data.get("permalink_url", "")
        }
    except Exception as e:
        print(f"Error fetching post data: {e}")
        return None

# ======== Flask routes ========
@app.route('/')
def home():
    return "البوت يعمل!"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge
    return "فشل", 403

@app.route('/webhook', methods=['POST'])
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
                    send_text_message(sender_id, "👋 أهلاً! أرسل لي رابط منشور فيسبوك")
                send_sender_action(sender_id, "typing_off")
    return "OK", 200

def handle_link(sender_id, url):
    send_text_message(sender_id, "⏳ جاري جلب المنشور...")
    post_id = extract_post_id(url)
    if not post_id:
        send_text_message(sender_id, "❌ لم أستطع تحديد معرف المنشور")
        return

    data = get_post_data(post_id)
    if not data:
        send_text_message(sender_id, "❌ لم أستطع الوصول للمنشور")
        return

    send_text_message(sender_id, data["title"])
    if data["image"]:
        send_text_message(sender_id, "🖼️ جاري إرسال الصورة...")
        send_image_message(sender_id, data["image"])
    else:
        send_text_message(sender_id, "ℹ️ لا توجد صورة في هذا المنشور")
    if data["url"]:
        send_text_message(sender_id, f"🔗 رابط المنشور:\n{data['url']}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
