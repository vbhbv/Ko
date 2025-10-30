import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
import asyncio
import openai
import json

# استيراد الإعدادات من ملف config.py
from config import BOT_TOKEN, ADMIN_ID, SOURCE_CHANNEL, OPENAI_API_KEY

# تهيئة OpenAI API
openai.api_key = OPENAI_API_KEY

# إعداد قاعدة البيانات (للقراءة فقط)
DB_NAME = "books_index.db"

# ===================================================
# دالة الذكاء الاصطناعي للبحث (AI Search Function)
# ===================================================
def intelligent_search_ai(user_query):
    """
    يستخدم الذكاء الاصطناعي لاستنتاج العنوان الأقرب من طلب المستخدم الغامض.
    """
    # 1. جلب قائمة العناوين المتاحة من قاعدة البيانات
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # سحب أول 10000 عنوان فقط لتوفير التكلفة وسرعة الـ API
        cursor.execute("SELECT title FROM books LIMIT 10000") 
        available_titles = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"خطأ في قراءة قاعدة البيانات: {e}")
        return None, "خطأ في الفهرسة الداخلية."

    # 2. بناء تعليمات AI
    titles_list_str = "\n".join(available_titles)
    
    prompt = f"""
    أنت نظام استنتاج كتب ذكي. مهمتك هي تحليل طلب المستخدم واستنتاج 
    عنوان الكتاب الأكثر احتمالاً الذي يبحث عنه من قائمة العناوين المتاحة.
    رد بعنوان الكتاب المطابق فقط، دون أي كلمات إضافية أو شرح. إذا لم تجد تطابقاً قريباً، أرسل "NOT_FOUND".

    قائمة العناوين المتاحة (للمساعدة): {titles_list_str[:3000]}
    
    طلب المستخدم: "{user_query}"
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a smart book inference system. Your goal is to infer the closest book title from the user's request. Respond ONLY with the title or 'NOT_FOUND'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50
        )
        ai_response = response.choices[0].message.content.strip()
        
        # 3. التحقق من تطابق نتيجة AI مع الفهرس
        if ai_response in available_titles:
             return ai_response, None
        else:
             return None, "لم يتم العثور على تطابق قريب في الفهرس."

    except Exception as e:
        error_msg = f"خطأ في الاتصال بـ OpenAI: {e}"
        print(error_msg)
        return None, "حدث خطأ في خدمة الذكاء الاصطناعي."

# ===================================================
# دوال معالجة أوامر تيليجرام
# ===================================================

async def start_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start."""
    await update.message.reply_text(
        "مرحباً بك في مكتبة المليون كتاب الذكية! 📚\n"
        "ما عليك سوى وصف الكتاب الذي تبحث عنه، وسيقوم الذكاء الاصطناعي بالبحث عنه في الفهرس الضخم."
    )

async def search_message(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج رسائل المستخدم للبحث الذكي.
    """
    user_query = update.message.text
    
    await update.message.reply_text("جاري البحث الذكي... 🧠")
    
    # 1. استنتاج العنوان باستخدام الذكاء الاصطناعي
    inferred_title, error = intelligent_search_ai(user_query)
    
    if error:
        await update.message.reply_text(f"عذراً، {error}")
        return

    # 2. البحث عن بيانات الكتاب في قاعدة البيانات المحلية (باستخدام العنوان المستنتج)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, author FROM books WHERE title = ?", (inferred_title,))
        book_data = cursor.fetchone()
        conn.close()
    except Exception:
        await update.message.reply_text("خطأ داخلي في قاعدة البيانات.")
        return

    # 3. إرسال الكتاب للمستخدم (باستخدام Message ID)
    if book_data:
        message_id, author = book_data
        
        # التأكد من أن البوت يمكنه قراءة القناة (في بعض الحالات يجب أن يكون البوت مشرفاً)
        # لكن التحويل (forward_message) يكفي طالما أن القناة عامة
        try:
            await context.bot.forward_message(
                chat_id=update.message.chat_id,
                from_chat_id=f"@{SOURCE_CHANNEL}", # استخدام اسم القناة
                message_id=message_id
            )
            await update.message.reply_text(
                f"✅ تم العثور على: **{inferred_title}** للمؤلف **{author}**.\n"
                f"تم تحويل الكتاب بنجاح!"
            )
        except telegram.error.TelegramError as e:
            await update.message.reply_text(
                f"❌ عذراً، لم أستطع تحويل الملف. قد تكون هناك قيود على النسخ في القناة."
            )
    else:
        await update.message.reply_text(f"لم يتم العثور على '{inferred_title}' في الفهرس.")


# ===================================================
# إعداد وتشغيل البوت
# ===================================================

def main():
    """تشغيل البوت."""
    # إنشاء تطبيق البوت
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # معالجات الأوامر
    application.add_handler(CommandHandler("start", start_command))
    
    # معالج الرسائل النصية (للبحث الذكي)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_message))

    print("🚀 البوت بدأ العمل! (اضغط Ctrl+C للإيقاف)")
    application.run_polling()

if __name__ == "__main__":
    main()
