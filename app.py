from flask import Flask, request
import requests
import re
import os
import html

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_token_123")

def send_text_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v16.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending text: {e}")
        return None

def send_image_message(recipient_id, image_url):
    url = f"https://graph.facebook.com/v16.0/me/messages"
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
        },
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"Image send result: {result}")
        return result
    except Exception as e:
        print(f"Error sending image: {e}")
        return None

def send_sender_action(recipient_id, action):
    url = f"https://graph.facebook.com/v16.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": action,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        requests.post(url, json=payload)
    except:
        pass

def extract_post_data(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # البحث عن الصورة بعدة طرق
        image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        
        # طريقة بديلة: twitter:image
        if not image_match:
            image_match = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        
        # طريقة ثالثة: image_src
        if not image_match:
            image_match = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', response.text)
        
        # البحث عن الوصف والعنوان
        desc_match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        
        # استخراج القيم
        title = html.unescape(title_match.group(1)) if title_match else "منشور فيسبوك"
        description = html.unescape(desc_match.group(1)) if desc_match else ""
        image = image_match.group(1) if image_match else None
        
        # تصحيح رابط الصورة إذا كان نسبياً
        if image and image.startswith('/'):
            from urllib.parse import urljoin
            image = urljoin(url, image)
        
        print(f"Extracted - Title: {title[:50]}, Image: {image}")
        
        return {
            'title': title,
            'description': description,
            'image': image,
            'url': url
        }
    except Exception as e:
        print(f"Error extracting: {e}")
        return None

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
    
    if data.get('object') != 'page':
        return "OK", 200
    
    for entry in data.get('entry', []):
        for event in entry.get('messaging', []):
            sender_id = event['sender']['id']
            
            if 'message' in event and 'text' in event['message']:
                text = event['message']['text']
                
                send_sender_action(sender_id, "typing_on")
                
                if 'facebook.com' in text or 'fb.com' in text:
                    handle_link(sender_id, text)
                else:
                    send_text_message(sender_id, "👋 أهلاً! أرسل لي رابط منشور فيسبوك")
                
                send_sender_action(sender_id, "typing_off")
    
    return "OK", 200

def handle_link(sender_id, url):
    send_text_message(sender_id, "⏳ جاري جلب المنشور...")
    
    data = extract_post_data(url)
    
    if not data:
        send_text_message(sender_id, "❌ لم أستطع الوصول للمنشور")
        return
    
    # إرسال النص
    message = data['title']
    if data['description']:
        message += "\n\n" + data['description']
    send_text_message(sender_id, message)
    
    # إرسال الصورة
    if data['image']:
        print(f"Sending image: {data['image']}")
        send_text_message(sender_id, "🖼️ جاري إرسال الصورة...")
        result = send_image_message(sender_id, data['image'])
        
        if result and 'error' in result:
            error_msg = result['error'].get('message', 'خطأ غير معروف')
            send_text_message(sender_id, f"⚠️ لم أستطع إرسال الصورة: {error_msg}")
            # إرسال رابط الصورة كبديل
            send_text_message(sender_id, f"🔗 يمكنك رؤية الصورة هنا:\n{data['image']}")
    else:
        send_text_message(sender_id, "ℹ️ لا توجد صورة في هذا المنشور")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
