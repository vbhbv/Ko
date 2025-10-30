# app/book_bot.py
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
import openai
import json
import logging

# تهيئة التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from config import BOT_TOKEN, OPENAI_API_KEY
except ImportError:
    logger.error("Error: config.py not found or incomplete.")
    exit()

# تهيئة OpenAI API
if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("Warning: OpenAI Key not configured. Smart search will be disabled.")

# إعداد قاعدة البيانات
DB_NAME = "books_index.db"

# ===================================================
# دالة الذكاء الاصطناعي للبحث
# ===================================================
def intelligent_search_ai(user_query):
    """
    Uses AI to infer the closest book title from the user's query.
    """
    if not openai.api_key:
        return None, "AI service not available. Check OPENAI_API_KEY."

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Fetch up to 10000 random titles for better AI context
        cursor.execute("SELECT title FROM books ORDER BY RANDOM() LIMIT 10000") 
        available_titles = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"DB Read Error: {e}")
        return None, "Internal indexing error (DB not found or empty)."

    if not available_titles:
        return None, "Indexing database is empty. Please run indexer.py first."

    titles_list_str = "\n".join(available_titles)
    
    prompt = f"""
    You are a smart book inference system. Infer the most likely book title from the user's request based on the available list.
    Respond ONLY with the exact matching book title or 'NOT_FOUND'.

    Available Titles (for context): {titles_list_str[:3000]}
    
    User Request: "{user_query}"
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a smart book inference system. Respond ONLY with the inferred title or 'NOT_FOUND'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50
        )
        ai_response = response.choices[0].message.content.strip()
        
        if ai_response in available_titles:
             return ai_response, None
        else:
             return None, "No close match found in the index."

    except Exception as e:
        logger.error(f"OpenAI API Error: {e}")
        return None, "AI service error occurred."

# ===================================================
# دوال معالجة أوامر تيليجرام
# ===================================================

async def start_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    await update.message.reply_text(
        "مرحباً بك في مكتبة الروابط الذكية! 📚\n"
        "صف الكتاب الذي تبحث عنه، وسيقوم الذكاء الاصطناعي بالبحث عنه في الفهرس الضخم وتقديم رابط التحميل المباشر."
    )

async def search_message(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user search queries."""
    user_query = update.message.text
    
    if len(user_query) < 5:
        await update.message.reply_text("الرجاء إدخال وصف أطول للبحث الذكي.")
        return

    await update.message.reply_text("جاري البحث الذكي... 🧠")
    
    inferred_title, error = intelligent_search_ai(user_query)
    
    if error:
        await update.message.reply_text(f"عذراً، {error}")
        return

    # 3. البحث عن بيانات الكتاب في قاعدة البيانات المحلية (باستخدام العنوان المستنتج)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT author, summary, download_link, source_url FROM books WHERE title = ?", (inferred_title,))
        book_data = cursor.fetchone()
        conn.close()
    except Exception:
        await update.message.reply_text("خطأ داخلي في قاعدة البيانات.")
        return

    # 4. إرسال رابط التحميل للمستخدم
    if book_data:
        author, summary, download_link, source_url = book_data
        
        message_text = (
            f"✅ **تم العثور على: {inferred_title}**\n"
            f"👤 **المؤلف:** {author}\n\n"
            f"📝 **الملخص:** {summary}\n\n"
            f"🔗 [رابط التحميل المباشر]({download_link})\n"
            f"🌐 **المصدر:** [اقرأ المزيد هنا]({source_url})"
        )
        
        await update.message.reply_text(
            message_text,
            parse_mode=telegram.constants.ParseMode.MARKDOWN,
            disable_web_page_preview=True 
        )
    else:
        await update.message.reply_text(f"لم يتم العثور على '{inferred_title}' في الفهرس.")


# ===================================================
# إعداد وتشغيل البوت
# ===================================================

def main():
    """Starts the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in config.py.")
        return

    # Creating the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_message))

    logger.info("🚀 Bot is running!")
    application.run_polling()

if __name__ == "__main__":
    main()
