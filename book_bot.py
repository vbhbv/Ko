import os
import logging
import requests
import asyncio
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from urllib.parse import urlparse

# ----------------------------------------------------------------------
# 1. إعدادات المتغيرات والمفاتيح
# ----------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("AI_KEY")

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعداد عميل OpenAI
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    logger.warning("❌ مفتاح AI_KEY غير موجود. سيتم تعطيل ميزة التحليل الذكي.")


# ----------------------------------------------------------------------
# 2. وظائف الذكاء الاصطناعي والبحث المتقدم
# ----------------------------------------------------------------------

async def get_synthesis_analysis(book_title: str) -> str:
    """
    يطلب تحليلاً عميقاً وتطبيقاً عملياً للكتاب من OpenAI (ناسك الحكمة).
    (الكود كما في الرد السابق، يستخدم GPT-4o-mini)
    """
    if not OPENAI_API_KEY:
        return "⚠️ لا يمكنني إنشاء تحليل، مفتاح AI_KEY مفقود. (الناسك في سبات عميق)."
    
    system_prompt = (
        "أنت 'ناسك الحكمة'، خبير أدبي وفيلسوف يحلل الكتب الأكثر شهرة عالمياً. "
        "مهمتك هي تقديم تحليل عميق ومحفز، يركز على الفكرة الأساسية للكتاب، "
        "وكيف يمكن للجمهور الحديث تطبيق دروسه الخالدة على تحدياتهم اليومية."
        "اجعل الإجابة مقسمة إلى ثلاث نقاط رئيسية (بشكل نقاط) وقدمها بأسلوب بلاغي مؤثر."
    )
    
    user_prompt = f"قدم تحليلك الأسطوري لكتاب بعنوان: '{book_title}'."
    
    try:
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=700
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في OpenAI API: {e}")
        return "❌ حدث خطأ أثناء محاولة استدعاء حكمة الناسك."

# ----------------------------------------------------------------------
# 3. وظيفة البحث البديلة (البحث العادي بدون API)
# ----------------------------------------------------------------------

async def simple_file_search(book_title: str) -> tuple[str | None, str | None]:
    """
    يقوم بالبحث عن رابط مباشر باستخدام استعلام بحث Google العادي
    بدون استخدام مفاتيح Google API المعقدة، مع التركيز على مواقع المكتبات.
    """
    
    # 🚨 تم دمج أفضل استراتيجية بحث هنا (بدون مفاتيح API)
    # سنستخدم استعلام بحث جوجل المباشر (Google Search Query)
    # هذا النوع من البحث يتم تنفيذه يدوياً من قبلنا، لا نحتاج مفتاح API هنا.
    
    search_query = f"ملف pdf كتاب {book_title} site:kutub.info OR site:pdf-books.org"
    
    # للأسف، لا يمكن تنفيذ بحث Google بشكل آلي داخل الكود بدون API أو مكتبات معقدة (مثل BeautifulSoup)
    # لحل المشكلة بشكل فوري والتحول إلى نموذج "الناسك والباحث"، سنحتاج إلى تبسيط الأمر:
    
    # **الحل المبتكر:** سنطلب من الذكاء الاصطناعي إنشاء رابط بحث Google مباشر (Google Search URL) 
    # يتميز بالجودة، ثم نطلب من المستخدم البحث يدوياً (كإجراء مؤقت) 
    # أو نستخدم طريقة إرسال الملفات إذا كان لديك ملف مخزن.
    
    # نظراً للقيود، فإن الطريقة الأكثر ابتكاراً هي إرسال ملفات **مخزنة مسبقاً**
    # أو **إرسال رابط البحث المباشر للمستخدم** للتحقق منه.

    # 💡 سنستخدم الآن نموذج "الرابط المباشر للبحث المتقدم":
    encoded_query = requests.utils.quote(search_query)
    google_search_url = f"https://www.google.com/search?q={encoded_query}&tbm=nws" # (تغيير نوع البحث اختياري)

    return None, google_search_url # نرجع رابط البحث بدلاً من الملف


# ----------------------------------------------------------------------
# 4. دوال تليجرام والمنطق الرئيسي
# ----------------------------------------------------------------------

# دالة /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 أهلاً بك في بوت ناسك الحكمة والباحث الحصري!\n"
        "أرسل اسم أي كتاب: سأمنحك تحليل الناسك الأسطوري (AI) وأبحث لك عن الملف المباشر (PDF).\n"
    )

# دالة التعامل مع الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book_title = update.message.text.strip()
    logger.info(f"تلقيت طلب تحليل وبحث عن: {book_title}")
    
    # 1. إظهار رسالة التشغيل
    await update.message.reply_text(
        f"⏳ الناسك يتأمل في حكمة كتاب '{book_title}'...\n"
        "جاري صياغة التحليل العميق والبحث عن الملف."
    )
    
    # 2. طلب التحليل الأسطوري (لا يؤثر عليه فشل البحث)
    analysis_result = await get_synthesis_analysis(book_title)
    
    # 3. محاولة البحث عن الملف
    pdf_link, search_url = await simple_file_search(book_title)

    # 4. تجميع الرسالة النهائية
    
    # إذا لم نتمكن من جلب ملف مباشر، سنرسل رابط بحث متقدم للمستخدم
    if not pdf_link:
        final_message = (
            f"📜 **التحليل الأسطوري لناسك الحكمة:**\n"
            f"**الكتاب المُحلل:** {book_title}\n\n"
            f"{analysis_result}\n\n"
            f"⬇️ **البحث المباشر عن الملف (PDF):**\n"
            f"لم أتمكن من جلب الملف بشكل آلي، لكن يمكنك زيارة هذا الرابط المخصص للعثور عليه مباشرةً:\n"
            f"[رابط البحث المتقدم]({search_url})"
        )
    else:
        # هذه الحالة لن تتحقق إلا إذا كان هناك API بحث قوي (محذوف حالياً)
        final_message = (
            f"📜 **التحليل الأسطوري لناسك الحكمة:**\n"
            f"**الكتاب المُحلل:** {book_title}\n\n"
            f"{analysis_result}\n\n"
            f"✅ **تم العثور على الملف!**\n"
            f"جاري إرسال الملف المباشر..."
        )
        
    await update.message.reply_markdown(final_message)
    
    # 💡 خطوة إضافية: إرسال الملف المباشر
    if pdf_link:
        try:
            # هنا يجب إضافة كود لتحميل الملف وإرساله باستخدام telegram.InputFile
            # هذا يتطلب أن يكون الرابط المكتشف (pdf_link) يعمل ومباشر لملف PDF
            
            # مثال على كود إرسال ملف (يتطلب أن يكون الملف موجوداً ومحملاً)
            response = requests.get(pdf_link, stream=True, timeout=30)
            response.raise_for_status()
            
            # استخدام اسم الكتاب كاسم للملف
            file_name = f"{book_title}.pdf"
            
            # إرسال الملف
            await update.message.reply_document(
                document=InputFile(response.content, filename=file_name), 
                caption=f"هذا هو ملف {book_title} الذي طلبه الناسك."
            )

        except Exception as e:
            logger.error(f"❌ فشل في تحميل وإرسال ملف PDF من الرابط: {e}")
            await update.message.reply_text(
                "❌ عذراً، فشلت عملية تحميل وإرسال الملف من الرابط الذي تم العثور عليه."
            )


# ----------------------------------------------------------------------
# 5. الدالة الرئيسية للتشغيل
# ----------------------------------------------------------------------

def main():
    telegram_token = os.environ.get("BOT_TOKEN") 
    
    if not telegram_token:
        logger.error("🚫 فشل البدء: لم يتم العثور على رمز التوكن (BOT_TOKEN).")
        return

    application = ApplicationBuilder().token(telegram_token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)) 

    logger.info("✅ بوت ناسك الحكمة والباحث الحصري يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
