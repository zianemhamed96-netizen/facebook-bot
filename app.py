from flask import Flask, request
import requests
import re
import os

app = Flask(name)

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
        print(f"Error: {e}")
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
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
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
        
        image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        desc_match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', response.text)
        
        return {
            'title': title_match.group(1) if title_match else "منشور فيسبوك",
            'description': desc_match.group(1) if desc_match else "",
            'image': image_match.group(1) if image_match else None,
            'url': url
        }
    except Exception as e:
        print(f"Error: {e}")
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
                    send_text_message(sender_id, "ارسل رابط منشور فيسبوك")
                
                send_sender_action(sender_id, "typing_off")
    
    return "OK", 200

def handle_link(sender_id, url):
    send_text_message(sender_id, "جاري جلب المنشور...")
    data = extract_post_data(url)
    
    if not data:
        send_text_message(sender_id, "لم استطع الوصول للمنشور")
        return
    
    message = data['title']
    if data['description']:
        message += "\n\n" + data['description']
    send_text_message(sender_id, message)
    
    if data['image']:
        send_image_message(sender_id, data['image'])

if name == 'main':
    app.run(host='0.0.0.0', port=10000)