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

if name == 'main':
    app.run(host='0.0.0.0', port=10000)