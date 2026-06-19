# Our Space — Phase 2 Documentation
# Complete Setup & Deployment Guide

---

## Project Structure

```
my3-e2e-phase2/
├── app/
│   ├── __init__.py
│   ├── settings.py       # Django settings (all env vars read here)
│   ├── urls.py           # Main URL routing (security gate on root)
│   └── wsgi.py           # WSGI entry point for gunicorn
├── core/
│   ├── __init__.py
│   ├── admin.py          # Django admin panel registration
│   ├── models.py         # All database models
│   ├── views.py          # All API endpoints
│   ├── urls.py           # API URL patterns
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
├── templates/
│   └── index.html        # Mini-app UI (single-page, dark fitness theme)
├── bot.py                # Telegram bot (keep-alive, reminders, AI, presence)
├── manage.py             # Django management CLI
├── requirements.txt      # Python dependencies
└── render.yaml           # Render deployment config
```

---

## STEP 1 — Create Telegram Bot

### 1.1 Get Bot Token from BotFather

1. Open Telegram, search `@BotFather`
2. Send `/newbot`
3. Choose a display name (e.g., "Our Space")
4. Choose a username (must end in `bot`, e.g., `our_space_2024_bot`)
5. **Copy the token** — it looks like: `7234567890:AAHxxxxxxxxxxxxxxxxxxxx`

### 1.2 Get Your Telegram ID

1. Search `@userinfobot` in Telegram
2. Send any message
3. It replies with your ID (e.g., `123456789`)
4. **Do the same for your partner** — you need both IDs

### 1.3 Set Menu Button (Blue Button Next to Text Box)

This is what opens the mini-app. You'll set the URL AFTER deploying (Step 3).

For now, just remember:
```
BotFather → /mybots → select your bot → Bot Settings → Menu Button → Edit Menu Button URL
```
You'll paste your Render URL here later.

---

## STEP 2 — Get External Service Keys

### 2.1 Cloudinary (Media Uploads — Free 25GB)

1. Go to https://cloudinary.com/users/register_free
2. Sign up (free plan)
3. Go to Dashboard → you'll see:
   - **Cloud Name** (e.g., `dxabc123`)
   - **API Key** (e.g., `123456789012345`)
   - **API Secret** (e.g., `abcDEF123ghi456`)
4. Copy all three — you'll need them in Render Environment Variables

### 2.2 Google Gemini API (AI Assistant — Free Tier)

1. Go to https://aistudio.google.com/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Select a project (or create new)
5. **Copy the API key** — it looks like: `AIzaSy...`

> The free tier allows ~15 requests/minute, 1M tokens/minute. More than enough for 2 people.

---

## STEP 3 — Deploy to Render

### 3.1 Push to GitHub

```bash
cd my3-e2e-phase2

# Initialize git (if not already)
git init
git add .
git commit -m "Phase 2: complete upgrade"

# Create a PRIVATE repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/your-private-repo.git
git branch -M main
git push -u origin main
```

> **IMPORTANT:** Keep the repo PRIVATE! This project has your personal data and security logic.

### 3.2 Create Web Service on Render

1. Go to https://dashboard.render.com
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Fill in:
   - **Name:** `our-space-app` (or whatever you like)
   - **Runtime:** Python
   - **Build Command:**
     ```
     pip install -r requirements.txt && python manage.py migrate --no-input && python manage.py collectstatic --no-input
     ```
   - **Start Command:**
     ```
     gunicorn app.wsgi:application --bind 0.0.0.0:$PORT --workers 1
     ```
   - **Plan:** Free

5. **WAIT** — don't create yet! First add Environment Variables (next step)

### 3.3 Environment Variables

In the Render web service creation page, scroll down to **Environment Variables** and add ALL of these:

| Key | Value | Required? | How to Get |
|-----|-------|-----------|------------|
| `DJANGO_SETTINGS_MODULE` | `app.settings` | YES | Fixed value |
| `SECRET_KEY` | (auto-generate) | YES | Click "Generate" in Render |
| `DEBUG` | `False` | YES | Fixed value |
| `ALLOWED_HOSTS` | `your-app.onrender.com` | YES | Your Render subdomain |
| `BOT_TOKEN` | `7234567890:AAHxxxx` | YES | From BotFather (Step 1.1) |
| `ALLOWED_TG_IDS` | `123456789,987654321` | YES | Your + partner's Telegram IDs (Step 1.2) |
| `WEB_APP_URL` | `https://your-app.onrender.com` | YES | Your Render URL (appears after deploy) |
| `CLOUDINARY_CLOUD_NAME` | `dxabc123` | YES | From Cloudinary Dashboard (Step 2.1) |
| `CLOUDINARY_API_KEY` | `123456789012345` | YES | From Cloudinary Dashboard (Step 2.1) |
| `CLOUDINARY_API_SECRET` | `abcDEF123ghi456` | YES | From Cloudinary Dashboard (Step 2.1) |
| `GEMINI_API_KEY` | `AIzaSy...` | NO* | From Google AI Studio (Step 2.2) |
| `MEDIA_RETENTION_DAYS` | `30` | NO | Days before auto-deleting media (default: 30) |

> *If GEMINI_API_KEY is not set, the AI tab will show "AI assistant not configured" but everything else works fine.

### 3.4 Deploy!

1. Click **Create Web Service**
2. Wait for build (~2-3 minutes)
3. Once deployed, note your URL: `https://your-app-name.onrender.com`

### 3.5 Set the Telegram Menu Button URL

Now go back to BotFather:
```
@BotFather → /mybots → select your bot → Bot Settings → Menu Button → Edit Menu Button URL
```
Paste: `https://your-app-name.onrender.com`

Done! The blue button now opens your mini-app.

---

## STEP 4 — Database Setup

### Option A: SQLite (Default — Simple but Resets on Deploy)

The default config uses SQLite. **Problem:** On Render's free plan, the filesystem is ephemeral — every deploy wipes the database.

Use this ONLY for testing. Your data will be lost on each deploy.

### Option B: Render PostgreSQL (RECOMMENDED — Free, Persistent)

This is the proper way. Data survives deploys and reboots.

**4.1 Create PostgreSQL Database on Render:**

1. Render Dashboard → **New** → **PostgreSQL**
2. Name: `our-space-db`
3. Plan: Free (90 days free, then $7/month. Or use the free tier which resets after 90 days)
4. Click **Create Database**
5. Wait for it to be available
6. Copy the **Internal Database URL** (looks like: `postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/dbname`)

**4.2 Update Your Project for PostgreSQL:**

Add these to your `requirements.txt`:
```
psycopg2-binary==2.9.9
dj-database-url==2.1.0
```

Update `app/settings.py` — replace the DATABASES section with:
```python
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    )
}
```

**4.3 Add DATABASE_URL to Render Environment Variables:**

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/dbname` |

Render can also auto-link: when you create the PostgreSQL database in the same Render account, you can link it to your web service and it automatically sets `DATABASE_URL`.

**4.4 Run Migrations:**

After updating, go to Render → your Web Service → **Shell**:
```bash
python manage.py migrate --no-input
python manage.py createsuperuser
```

### Option C: External Free PostgreSQL (Alternative)

If Render PostgreSQL free tier expired, use:
- **Supabase** (free PostgreSQL): https://supabase.com
- **Neon** (free PostgreSQL): https://neon.tech
- **ElephantSQL** (free tiny plan): https://www.elephantsql.com

Get the PostgreSQL URL and add it as `DATABASE_URL` environment variable — same as Option B step 4.3.

---

## STEP 5 — Bot Worker Setup (Optional but Recommended)

The bot.py provides:
- **Keep-alive ping** (every 7 minutes — prevents Render from sleeping)
- **Call date reminders** (notifies 1 day before a scheduled call)
- **/status command** (check partner's online status)
- **/ai command** (ask AI assistant from Telegram directly)

### Option A: Run bot.py as Render Worker (Best)

1. In `render.yaml`, uncomment the worker section
2. Or manually: Render Dashboard → **New** → **Background Worker**
3. Connect same repo
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
6. Add same env vars: `BOT_TOKEN`, `WEB_APP_URL`, `GEMINI_API_KEY`, `ALLOWED_TG_IDS`

### Option B: Run on Railway (Free Alternative)

1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Select your repo
4. Start Command: `python bot.py`
5. Add env vars: `BOT_TOKEN`, `WEB_APP_URL`, `GEMINI_API_KEY`, `ALLOWED_TG_IDS`

### Option C: Run Locally (Simplest)

```bash
# In a terminal, 24/7:
cd my3-e2e-phase2
export BOT_TOKEN="your-token"
export WEB_APP_URL="https://your-app.onrender.com"
export GEMINI_API_KEY="your-key"
export ALLOWED_TG_IDS="123,456"
python bot.py
```

> Without the bot worker, the keep-alive won't work and Render may sleep after 15 min of inactivity.
> You can use UptimeRobot (https://uptimerobot.com) as an alternative — set it to ping `https://your-app.onrender.com/api/keep-alive/` every 5 minutes.

---

## STEP 6 — Create Admin User

You need an admin user to access `/admin-panel/` for managing data.

### On Render:

1. Go to your Web Service → **Shell** (left sidebar)
2. Run:
```bash
python manage.py createsuperuser
```
3. Enter username, email, password
4. Go to `https://your-app.onrender.com/admin-panel/`
5. Login with those credentials

### Locally:

```bash
cd my3-e2e-phase2
python manage.py createsuperuser
python manage.py runserver
# Go to http://localhost:8000/admin-panel/
```

---

## STEP 7 — Test Everything

### 7.1 Test Mini-App

1. Open Telegram
2. Find your bot
3. Send `/start` → tap "Open App" button
4. The mini-app should load with the dark fitness theme
5. Try creating a note, routine, and todo

### 7.2 Test Security

1. Open your Render URL in a browser (e.g., Chrome)
2. You should ONLY see: `{"status":"live","bot":"online","message":"Bot is Live",...}`
3. The full app is NOT accessible from a browser — only from Telegram

### 7.3 Test Media Upload

1. In the Notes tab, tap the camera or video icon
2. Select a photo/video/audio file
3. Add text (optional) and send
4. The media should appear in the note with a Cloudinary URL

### 7.4 Test AI Assistant

1. Go to the AI tab (🤖)
2. Type a message and press Ask
3. Gemini should respond within a few seconds

### 7.5 Test Presence

1. Open the app — your status should show as "online" (green dot)
2. Close the app — partner should see you as "offline" (gray dot)
3. Use `/status` command in bot (if bot worker is running)

### 7.6 Test Call Date Reminder

1. Create a todo with "📞 This is a call/meeting" checked
2. Set the date to tomorrow
3. The bot will notify both you and your partner (if bot worker is running)

---

## Complete API Reference

### Authentication
All endpoints require `tg_id` parameter. Only IDs in `ALLOWED_TG_IDS` can access data.

### Core Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/dashboard/?tg_id=...` | Load all data (notes, todos, routines, presence) |
| GET | `/api/status/` | Public status page ("Bot is Live") |
| GET | `/api/keep-alive/` | Keep-alive ping endpoint |

### Notes

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/notes/add/` | `{tg_id, text, mood_tag, media_file?, media_type?}` | Create note (multipart for media) |
| DELETE | `/api/notes/<id>/?tg_id=...` | — | Delete note (author only) |

### Todos

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/todos/add/` | `{tg_id, title, emoji?, priority?, is_private?, scheduled_date?, scheduled_time?, is_call_date?}` | Create todo |
| POST | `/api/todos/<id>/toggle/` | `{tg_id}` | Toggle done/undone |
| DELETE | `/api/todos/<id>/?tg_id=...` | — | Delete todo (owner only) |

### Routines

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/routines/add/` | `{tg_id, title, emoji?, frequency?, scheduled_time?}` | Create routine |
| POST | `/api/routines/<id>/check/` | `{tg_id}` | Check/uncheck for today |
| DELETE | `/api/routines/<id>/?tg_id=...` | — | Delete routine (owner only) |

### Vibe

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/vibe/update/` | `{tg_id, emoji, label}` | Update your vibe |

### Presence

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/presence/offline/` | `{tg_id}` | Mark user as offline |
| GET | `/api/presence/status/` | — | Get online status of all users |

### AI Chat

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/ai/chat/` | `{tg_id, message}` | Send message to Gemini AI |

### Games

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `/api/game/score/` | `{tg_id, game_type, score}` | Submit game score |
| GET | `/api/leaderboard/` | — | Get leaderboard |

### System

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/media/cleanup/` | Trigger media cleanup (removes files older than MEDIA_RETENTION_DAYS) |

---

## Environment Variables — Complete Reference

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | YES | `app.settings` | Django settings module |
| `SECRET_KEY` | YES | (auto-generated) | Django secret key for crypto |
| `DEBUG` | YES | `False` | Debug mode (always False in production) |
| `ALLOWED_HOSTS` | YES | `our-space-app.onrender.com` | Allowed domain names |
| `BOT_TOKEN` | YES | `7234567890:AAHxxxx` | Telegram bot token |
| `ALLOWED_TG_IDS` | YES | `123456789,987654321` | Comma-separated allowed Telegram user IDs |
| `WEB_APP_URL` | YES | `https://our-space-app.onrender.com` | Full URL of deployed app |
| `CLOUDINARY_CLOUD_NAME` | YES | `dxabc123` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | YES | `123456789012345` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | YES | `abcDEF123ghi456` | Cloudinary API secret |
| `GEMINI_API_KEY` | NO | `AIzaSy...` | Google Gemini API key (AI feature) |
| `DATABASE_URL` | NO | `postgresql://...` | PostgreSQL connection string (if using Postgres) |
| `MEDIA_RETENTION_DAYS` | NO | `30` | Days before auto-deleting media from Cloudinary |

---

## Local Development

```bash
# 1. Clone the repo
cd my3-e2e-phase2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (or create .env file)
export BOT_TOKEN="your-token"
export WEB_APP_URL="http://localhost:8000"
export ALLOWED_TG_IDS="123456789,987654321"
export DEBUG="True"
export CLOUDINARY_CLOUD_NAME="your-cloud"
export CLOUDINARY_API_KEY="your-key"
export CLOUDINARY_API_SECRET="your-secret"
export GEMINI_API_KEY="your-key"

# 4. Run migrations
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Start server
python manage.py runserver

# 7. Open in browser
# Mini-app: http://localhost:8000
# Admin: http://localhost:8000/admin-panel/
# API test: http://localhost:8000/api/dashboard/?tg_id=12345&name=Test

# 8. Run bot (separate terminal)
python bot.py
```

---

## Troubleshooting

### "Connection error" when opening the app
- Check that Render service is running (may need cold start ~30s)
- Verify `WEB_APP_URL` matches your actual Render URL
- Check Render logs for errors

### Media upload fails
- Verify Cloudinary credentials are correct
- Check Render logs for "Cloudinary upload error"
- Make sure file size is under 20MB

### AI not responding
- Verify `GEMINI_API_KEY` is set correctly
- Check that the API key is valid at https://aistudio.google.com/apikey
- Free tier has rate limits (~15 requests/min)

### Database keeps resetting
- You're using SQLite on Render's ephemeral filesystem
- Switch to PostgreSQL (see Step 4, Option B)

### Render keeps sleeping
- Set up the bot worker (keep-alive every 7 minutes)
- Or use UptimeRobot to ping `/api/keep-alive/` every 5 minutes

### "Access denied" error
- Make sure your Telegram ID is in `ALLOWED_TG_IDS`
- IDs must be comma-separated numbers (no spaces)

### Browser shows "Bot is Live" instead of the app
- This is CORRECT behavior! The app only works inside Telegram
- Open the bot in Telegram and tap "Open App"

---

## Security Notes

1. **Keep your repo private** — the code contains your security logic
2. **Never commit .env files** — use Render Environment Variables
3. **ALLOWED_TG_IDS** is your access control — only listed users can see data
4. **Non-Telegram visitors** only see `{"status": "live", "bot": "online"}`
5. **Media files** auto-delete after 30 days (configurable via MEDIA_RETENTION_DAYS)
6. **Cloudinary** media is served over HTTPS — secure and fast

---

## Phase 2 Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Security gate | ✅ | Non-Telegram = "Bot is Live" only |
| ALLOWED_TG_IDS | ✅ | Only 2 users can access |
| Keep-alive | ✅ | Bot pings every 7 min |
| Media upload | ✅ | Image, video, audio, GIF via Cloudinary |
| Media cleanup | ✅ | Auto-delete after 30 days |
| Delete notes | ✅ | With Cloudinary cleanup |
| Delete routines | ✅ | Soft delete |
| Delete todos | ✅ | Owner only |
| Scheduled time (routines) | ✅ | Optional time per routine |
| Scheduled date/time (todos) | ✅ | Full date + time scheduling |
| Call date reminders | ✅ | 1-day before notification via bot |
| Presence tracking | ✅ | Online/offline + green dot |
| AI assistant | ✅ | Gemini 2.0 Flash |
| Dark fitness theme | ✅ | Black + neon orange + metallic silver |
| English language | ✅ | All UI text in English |
| 6 tabs | ✅ | Routine, Notes, Tasks, AI, Games, Rank |
