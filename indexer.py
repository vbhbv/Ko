# indexer.py
import sqlite3
import requests
from bs4 import BeautifulSoup
import openai
import json
import time
import random
import logging

# تهيئة التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from config import OPENAI_API_KEY
except ImportError:
    logger.error("خطأ: لم يتم العثور على config.py")
    exit()

# تهيئة AI
openai.api_key = OPENAI_API_KEY
DB_NAME = "books_index.db"

# ===================================================
# 1. إعداد قاعدة البيانات
# ===================================================
def setup_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            title TEXT UNIQUE,
            author TEXT,
            source_url TEXT,
            download_link TEXT,
            summary TEXT
        )
    """)
    conn.commit()
    return conn

# ===================================================
# 2. دالة جلب البيانات باستخدام الـ AI للتنظيف
# ===================================================
def clean_data_with_ai(raw_title, raw_summary):
    """يستخدم الـ AI لتنظيف وتحسين البيانات الوصفية للكتاب."""
    prompt = f"""
    قم بتنظيف وتحليل البيانات التالية:
    1. استخرج العنوان الدقيق والمؤلف من '{raw_title}'.
    2. لخص '{raw_summary}' في جملتين فقط.
    
    رد بصيغة JSON فقط: {{'title': '...', 'author': '...', 'summary': '...'}}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data cleaning and summarization expert. Respond ONLY with the requested JSON object."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=250
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"خطأ في تنظيف البيانات باستخدام AI: {e}")
        return None

# ===================================================
# 3. دالة جلب البيانات من موقع معين (مثال: مكتبة النور)
# *ملاحظة: تحتاج إلى تخصيص هذا الكود لكل موقع*
# ===================================================
def scrape_noorbook(conn):
    base_url = "https://www.noor-book.com/ar/books"
    logger.info(f"بدء جلب البيانات من: {base_url}")
    
    # سنفهرس أول 5 صفحات كمثال (لأن الفهرسة الكاملة مع AI تستغرق وقتاً وتكلفة)
    for page in range(1, 6): 
        try:
            response = requests.get(f"{base_url}?page={page}", timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # العثور على كل كارت كتاب
            book_cards = soup.find_all('div', class_='book-card') 

            for card in book_cards:
                try:
                    # استخراج رابط صفحة الكتاب
                    book_link = card.find('a', class_='book-cover')['href']
                    full_link = f"https://www.noor-book.com{book_link}"
                    
                    # استخراج العنوان الأولي (قد يكون غير نظيف)
                    raw_title = card.find('h4', class_='book-title').text.strip()
                    
                    # **[هنا تحتاج إلى زيارة كل صفحة جُزئياً لجلب رابط التنزيل والملخص]**
                    
                    # *لغرض التوضيح، سنفترض أننا حصلنا على البيانات*
                    raw_summary = "ملخص مؤقت لغرض الاختبار."
                    download_link = "http://example.com/download/book.pdf" 
                    
                    # استخدام AI لتنظيف البيانات
                    ai_data = clean_data_with_ai(raw_title, raw_summary)
                    
                    if ai_data:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR IGNORE INTO books 
                            (title, author, source_url, download_link, summary)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            ai_data['title'],
                            ai_data['author'],
                            full_link,
                            download_link,
                            ai_data['summary']
                        ))
                        conn.commit()
                        logger.info(f"✅ تم فهرسة: {ai_data['title']}")
                    
                    # انتظار لمنع الحظر
                    time.sleep(random.uniform(2, 5)) 

                except Exception as e:
                    logger.error(f"خطأ في معالجة كارت كتاب: {e}")
                    continue
            
            logger.info(f"انتهت الصفحة رقم: {page}")
        
        except Exception as e:
            logger.error(f"خطأ في جلب الصفحة {page}: {e}")
            break

# ===================================================
# 4. دالة التشغيل الرئيسية
# ===================================================
def main_indexer():
    conn = setup_db()
    
    # تنفيذ الفهرسة لكل موقع
    scrape_noorbook(conn) 
    # يمكنك إضافة دوال لـ "scrape_kotobati" و "scrape_alkutub" هنا.

    conn.close()
    logger.info("🎉 اكتملت عملية الفهرسة من جميع المصادر!")

if __name__ == "__main__":
    main_indexer()
