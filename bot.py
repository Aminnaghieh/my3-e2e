"""
bot.py
======
Telegram bot with Phase 2 features:
  - /start with mini-app launcher
  - Self-ping keep-alive (every 7 minutes)
  - Call date reminders (notify 1 day before)
  - Presence notifications (when partner comes online)
  - AI assistant command
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://your-app.onrender.com")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start - shows the mini-app launcher button."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="Open App",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ])

    await update.message.reply_text(
        text=(
            "Welcome! Your private workspace is ready.\n"
            "Tap the button below to open the app.\n\n"
            "Commands:\n"
            "/start - Open the app\n"
            "/status - Check partner status\n"
            "/ai <message> - Ask AI assistant\n"
            "/help - Show all commands"
        ),
        reply_markup=keyboard,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if your partner is currently online."""
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    django.setup()

    from core.models import TelegramUser

    # Get the caller
    tg_id = update.effective_user.id
    try:
        user = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        await update.message.reply_text("You are not registered yet. Open the app first!")
        return

    # Get partner
    partners = TelegramUser.objects.exclude(telegram_id=tg_id)
    if not partners.exists():
        await update.message.reply_text("No partner registered yet.")
        return

    partner = partners.first()
    status_icon = "online" if partner.is_online else "offline"
    last_seen = partner.last_seen.strftime("%H:%M on %b %d")

    await update.message.reply_text(
        f"Partner Status:\n"
        f"  {partner.first_name}: {status_icon}\n"
        f"  Last seen: {last_seen}\n"
        f"  Vibe: {partner.vibe_emoji} {partner.vibe_label}"
    )


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI assistant command: /ai <your question>"""
    if not context.args:
        await update.message.reply_text(
            "Usage: /ai <your question>\n\n"
            "Example: /ai What's a good workout for building muscle?"
        )
        return

    message = " ".join(context.args)

    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    django.setup()

    from core.models import TelegramUser, AIChatLog
    from django.conf import settings as django_settings

    if not django_settings.GEMINI_API_KEY:
        await update.message.reply_text("AI assistant is not configured yet.")
        return

    tg_id = update.effective_user.id
    try:
        user = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        user = TelegramUser.objects.create(
            telegram_id=tg_id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username or "",
        )

    # Save user message
    AIChatLog.objects.create(user=user, role="user", content=message)

    # Get recent context
    recent = AIChatLog.objects.filter(user=user).order_by("-created_at")[:10]
    history = list(reversed(list(recent)))

    try:
        import google.generativeai as genai
        genai.configure(api_key=django_settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        chat_history = []
        for msg in history[:-1]:
            chat_history.append({
                "role": "model" if msg.role == "assistant" else "user",
                "parts": [msg.content]
            })

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(message)
        ai_response = response.text

        AIChatLog.objects.create(user=user, role="assistant", content=ai_response)

        # Telegram message limit is 4096 chars
        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."

        await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"AI command error: {e}")
        await update.message.reply_text(f"AI error: {str(e)[:200]}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands."""
    await update.message.reply_text(
        "Available Commands:\n\n"
        "/start - Open the mini-app\n"
        "/status - Check partner online status\n"
        "/ai <message> - Ask the AI assistant\n"
        "/help - Show this help message\n\n"
        "The app supports:\n"
        "- Notes with images, video, audio, GIFs\n"
        "- Routines with scheduled times\n"
        "- To-dos with dates, times, and call reminders\n"
        "- AI assistant for fitness & productivity\n"
        "- Real-time presence tracking"
    )


async def post_init(application):
    """Set the menu button after bot initialization."""
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Open App",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    logger.info(f"Menu button set -> {WEB_APP_URL}")

    # Start background tasks
    asyncio.create_task(keep_alive_loop(application))
    asyncio.create_task(call_date_reminder_loop(application))


async def keep_alive_loop(application):
    """
    Self-ping the Render app every 7 minutes to prevent sleeping.
    Uses the /api/keep-alive/ endpoint.
    """
    import aiohttp
    while True:
        try:
            await asyncio.sleep(420)  # 7 minutes
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{WEB_APP_URL}/api/keep-alive/", timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        logger.info("Keep-alive ping successful")
                    else:
                        logger.warning(f"Keep-alive ping failed: {resp.status}")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")


async def call_date_reminder_loop(application):
    """
    Check for upcoming call dates every hour.
    If a call is scheduled for tomorrow, notify the partner.
    """
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            await check_call_dates(application)
        except Exception as e:
            logger.error(f"Call date reminder error: {e}")


async def check_call_dates(application):
    """Check for call dates scheduled for tomorrow and notify."""
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    django.setup()

    from core.models import ToDoList, TelegramUser
    from django.utils import timezone

    tomorrow = timezone.now().date() + timedelta(days=1)
    now = timezone.now()

    # Find call dates scheduled for tomorrow
    call_dates = ToDoList.objects.filter(
        is_call_date=True,
        is_done=False,
        scheduled_date=tomorrow,
    ).select_related("owner")

    for call in call_dates:
        # Notify the partner
        partners = TelegramUser.objects.exclude(telegram_id=call.owner.telegram_id)
        for partner in partners:
            time_str = call.scheduled_time.strftime("%H:%M") if call.scheduled_time else "No time set"
            try:
                await application.bot.send_message(
                    chat_id=partner.telegram_id,
                    text=(
                        f"Reminder! Call with {call.owner.first_name} tomorrow!\n"
                        f"  Title: {call.emoji} {call.title}\n"
                        f"  Date: {tomorrow.strftime('%b %d')}\n"
                        f"  Time: {time_str}\n\n"
                        f"Don't forget to reach out!"
                    )
                )
                logger.info(f"Call reminder sent to {partner.first_name}")
            except Exception as e:
                logger.error(f"Failed to send call reminder: {e}")

        # Also notify the owner
        try:
            await application.bot.send_message(
                chat_id=call.owner.telegram_id,
                text=(
                    f"Reminder: You have a call scheduled for tomorrow!\n"
                    f"  {call.emoji} {call.title}\n"
                    f"  Time: {time_str}"
                )
            )
        except Exception as e:
            logger.error(f"Failed to send call reminder to owner: {e}")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set! Add it to environment variables.")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
