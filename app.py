import os
from flask import Flask, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                if messaging_event.get('message'):
                    if 'text' in messaging_event['message']:
                        text = messaging_event['message']['text']
                        send_sender_action(sender_id, "typing_on")
                        # التحقق من الرابط
                        if 'facebook.com' in text or 'fb.com' in text:
                            handle_link(sender_id, text)
                        else:
                            send_text_message(sender_id,
                                "👋 أهلاً! أرسل لي رابط منشور فيسبوك\n"
                                "مثال: https://facebook.com/user/posts/123456")

                        send_sender_action(sender_id, "typing_off")

    return "OK", 200

def handle_link(sender_id, url):
    """معالجة رابط المنشور"""
    send_text_message(sender_id, "⏳ جاري جلب المنشور...")

    data = extract_post_data(url)

    if not data:
        send_text_message(sender_id, "❌ لم أستطع الوصول للمنشور. تأكد أنه عام.")
        return

    # إرسال النص
    message = f"📝 {data['title']}"
    if data['description']:
        message += f"\n\n{data['description']}"
    send_text_message(sender_id, message)

    # إرسال الصورة (الجزء المهم!)
    if data['image']:
        send_text_message(sender_id, "🖼️ جاري إرسال الصورة...")
        result = send_image_message(sender_id, data['image'])

        if result and 'error' in result:
            send_text_message(sender_id, f"⚠️ لم أستطع إرسال الصورة مباشرة، لكن يمكنك رؤيتها هنا:\n{data['image']}")
    else:
        send_text_message(sender_id, "ℹ️ لا توجد صورة في هذا المنشور")

def send_text_message(recipient_id, message_text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post("https://graph.facebook.com/v17.0/me/messages", params=params, headers=headers, json=data)
    return response.json()

def send_sender_action(recipient_id, action):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    requests.post("https://graph.facebook.com/v17.0/me/messages", params=params, headers=headers, json=data)

def send_image_message(recipient_id, image_url):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url}
            }
        }
    }
    response = requests.post("https://graph.facebook.com/v17.0/me/messages", params=params, headers=headers, json=data)
    return response.json()

def extract_post_data(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title = soup.find('title').text if soup.find('title') else "No title"

        # Extract description (meta description)
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        description = desc_meta['content'] if desc_meta else ""

        # Extract image (og:image)
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        image = og_image['content'] if og_image else None

        return {
            'title': title,
            'description': description,
            'image': image
        }
    except:
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)