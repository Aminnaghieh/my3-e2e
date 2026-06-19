import logging
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# لینک دیپلوی شده پروژه شما روی Render
WEB_APP_URL = "https://your-app-name.onrender.com"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر استارت ربات که دکمه باز کردن مینی‌اپ را نشان می‌دهد"""
    keyboard = [
        [KeyboardButton(text="💖 ورود به دنیای ما", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "سلام عشقم! 💕 روی دکمه زیر بزن تا وارد اپ اختصاصیمون بشیم.",
        reply_markup=reply_markup
    )

def main():
    """اجرای ربات"""
    # توکن ربات شما
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    application.add_handler(CommandHandler("start", start))
    
    # پینگ نگه داشتن سرور (اختیاری برای پلن رایگان)
    application.run_polling()

if __name__ == "__main__":
    main()