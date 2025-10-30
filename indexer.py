import pyrogram
import sqlite3
import time
import asyncio
from config import API_ID, API_HASH, SOURCE_CHANNEL, OPENAI_API_KEY # استيراد المفاتيح

# إعداد قاعدة البيانات
DB_NAME = "books_index.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# إنشاء جدول الفهرس إذا لم يكن موجوداً
cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY,
        message_id INTEGER UNIQUE,
        title TEXT,
        author TEXT,
        file_id TEXT,
        publish_date TEXT
    )
""")
conn.commit()

# تهيئة عميل Pyrogram
app = pyrogram.Client(
    "indexer_session", 
    api_id=API_ID, 
    api_hash=API_HASH
)

# ===================================================
# دالة التحليل الذكي باستخدام الذكاء الاصطناعي (AI Parsing)
# *هذه الدالة تستخدم مفتاح OpenAI الخاص بك لتحليل النص المعقد*
# ===================================================
def intelligent_parse(raw_text):
    """
    يستخدم الذكاء الاصطناعي (GPT) لاستخلاص العنوان والمؤلف بدقة عالية 
    من نص الرسالة غير المنظم. 
    """
    import openai 
    openai.api_key = OPENAI_API_KEY

    prompt = f"""
    أنت محلل بيانات ذكي. حلل النص التالي واستخرج منه بدقة:
    1. العنوان الكامل للكتاب (title).
    2. اسم المؤلف (author).
    
    الرد يجب أن يكون بصيغة JSON فقط. إذا لم تجد العنوان، استخدم "عنوان غير معروف".
    
    النص: "{raw_text[:1000]}"
    """ # يتم اقتطاع النص الطويل لحماية الـ API Limit
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data extraction expert. Extract the book title and author as a JSON object: {'title': '...', 'author': '...'}. Reply ONLY with the JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=150
        )
        
        # تحليل استجابة الذكاء الاصطناعي
        import json
        ai_data = json.loads(response.choices[0].message.content)
        return ai_data

    except Exception as e:
        print(f"⚠️ خطأ في تحليل AI: {e}")
        return {"title": "عنوان غير معروف", "author": "مؤلف غير معروف"}


# ========== دالة الفهرسة الرئيسية ==========
async def start_indexing():
    await app.start()
    print("✅ تم الاتصال بحسابك. بدء عملية فهرسة قناة @lovekotob...")

    last_message_id = 0
    total_indexed = 0

    while True:
        try:
            # جلب الرسائل على دفعات (دفعة بحد أقصى 100 رسالة)
            messages = await app.get_history(
                SOURCE_CHANNEL, 
                limit=100, 
                offset_id=last_message_id
            )
        except Exception as e:
            print(f"❌ خطأ في جلب سجل الرسائل: {e}")
            break

        if not messages:
            break

        for message in messages:
            # نتأكد من أن الرسالة ملف (كتاب) ولها نص
            if message.document and (message.caption or message.text):
                
                raw_text = message.caption or message.text
                
                # استخدام التحليل الذكي (AI) لاستخلاص البيانات
                extracted_data = intelligent_parse(raw_text)
                
                extracted_title = extracted_data.get("title", "عنوان غير معروف")
                extracted_author = extracted_data.get("author", "مؤلف غير معروف")
                
                if extracted_title != "عنوان غير معروف":
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO books 
                            (message_id, title, author, file_id, publish_date)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            message.id,
                            extracted_title,
                            extracted_author,
                            message.document.file_id, 
                            str(message.date)
                        ))
                        total_indexed += 1
                    except Exception as e:
                        print(f"⚠️ خطأ في حفظ الرسالة {message.id} في DB: {e}")
            
            last_message_id = message.id # تحديث لآخر رسالة تمت معالجتها

        conn.commit()
        print(f"تم فهرسة دفعة جديدة. إجمالي الكتب المفهرسة: {total_indexed}. آخر معرّف رسالة: {last_message_id}")
        # انتظار قصير لتجنب قيود تليجرام
        time.sleep(1.5) 

    print("🎉 اكتملت عملية فهرسة القناة بالكامل!")
    await app.stop()
    conn.close()

# تشغيل الدالة
if __name__ == "__main__":
    asyncio.run(start_indexing())
    
