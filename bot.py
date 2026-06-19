"""
bot.py
======
ربات تلگرام که مینی‌اپ رو باز می‌کنه.

این فایل رو می‌تونید به عنوان یه process جداگانه اجرا کنید
یا همون bot.py قدیمی رو نگه دارید برای forwarding پیام‌ها.

در Render:
  - سرویس اول (Web Service): Django → gunicorn app.wsgi
  - سرویس دوم (Worker): این bot.py

ولی با پلن رایگان Render فقط یه worker داریم.
راه‌حل: می‌تونیم ربات رو روی یه سرویس جداگانه (Railway, Fly.io)
        یا با webhook (زیر توضیح داده شده) ادغام کنیم.

متغیر محیطی لازم:
  BOT_TOKEN     → توکن از BotFather
  WEB_APP_URL   → URL دیپلوی شده Django روی Render
"""

import os
import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, MenuButton, MenuButtonWebApp
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://your-app.onrender.com")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هندلر /start
    ─────────────
    یه دکمه Inline نشون می‌ده که مینی‌اپ رو داخل تلگرام باز می‌کنه.
    این دکمه از نوع web_app هست - تلگرام خودش هندلش می‌کنه.
    """
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="⚡ باز کردن اپ",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ])

    await update.message.reply_text(
        text=(
            "سلام! 👋\n"
            "روی دکمه زیر بزن تا اپ باز بشه."
        ),
        reply_markup=keyboard,
    )


async def post_init(application):
    """
    بعد از init ربات، دکمه منوی اصلی رو ست می‌کنیم.
    این کاری میکنه که دکمه آبی «اپ» کنار تکست باکس نمایش داده بشه.

    ─── مهم ───
    این همون چیزیه که می‌خواستید: آیکون آبی کنار chat input
    تلگرام این رو "Menu Button" می‌نامه.
    """
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="⚡ اپ ما",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    logger.info(f"Menu button set → {WEB_APP_URL}")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده! در Render آن را در Environment Variables اضافه کنید.")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)  # ← ست کردن دکمه آبی
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
