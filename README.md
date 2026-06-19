# 🚀 Couple Routine Mini App
یه مینی‌اپ تلگرام برای روتین مشترک دونفره | Django + SQLite + Render

---

## ساختار پروژه

```
couple-routine/
├── app/
│   ├── settings.py      # تنظیمات Django
│   ├── urls.py          # URL routing اصلی
│   └── wsgi.py          # entry point برای gunicorn
├── core/
│   ├── models.py        # مدل‌های دیتابیس
│   ├── views.py         # تمام API endpointها
│   ├── urls.py          # URL routing اپ
│   └── admin.py         # پنل ادمین
├── templates/
│   └── index.html       # مینی‌اپ (کل UI)
├── bot.py               # ربات تلگرام
├── requirements.txt
└── render.yaml          # تنظیمات Render
```

---

## مرحله ۱ — آماده‌سازی ربات در BotFather

```
1. به @BotFather پیام بدید
2. /newbot بزنید → اسم و username بدید
3. توکن رو کپی کنید (مثل: 7234567890:AAHxxxx)
4. /mybots → اسم بات → Bot Settings → Menu Button
   → Edit Menu Button → آدرس Render (بعداً تکمیل میشه)
```

---

## مرحله ۲ — دیپلوی روی Render

### ۲.۱ ریپو رو آپلود کنید
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/شما/couple-routine.git
git push -u origin main
```

### ۲.۲ Web Service روی Render بسازید
```
1. render.com → New → Web Service
2. ریپو رو connect کنید
3. Build Command:
   pip install -r requirements.txt && python manage.py migrate --no-input && python manage.py collectstatic --no-input
4. Start Command:
   gunicorn app.wsgi:application --bind 0.0.0.0:$PORT --workers 1
5. Plan: Free
```

### ۲.۳ Environment Variables (در Render → Environment)
| کلید | مقدار |
|------|-------|
| `SECRET_KEY` | یه رشته تصادفی ۵۰+ کاراکتری |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app.onrender.com` |
| `BOT_TOKEN` | توکن از BotFather |
| `ALLOWED_TG_IDS` | آیدی تلگرام شما و دوست‌دخترتون (مثل `123456789,987654321`) |
| `WEB_APP_URL` | آدرس Render شما (مثل `https://couple-routine.onrender.com`) |

> **آیدی تلگرام رو اینطوری پیدا کنید:** به @userinfobot پیام بدید

---

## مرحله ۳ — وصل کردن بات به مینی‌اپ

### روش A: دکمه آبی کنار تکست‌باکس (Menu Button) ← این که می‌خواستید

دو راه داره:

**راه ۱ — از طریق BotFather (ساده‌تر):**
```
1. /mybots → انتخاب بات → Bot Settings → Menu Button
2. Edit Menu Button URL → آدرس Render رو بزنید
3. تمام! دکمه آبی "اپ ما" کنار تکست‌باکس ظاهر میشه
```

**راه ۲ — از طریق bot.py (خودکار):**
```python
# bot.py داخل post_init این رو اجرا می‌کنه:
await application.bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(text="⚡ اپ ما", web_app=WebAppInfo(url=WEB_APP_URL))
)
```

### روش B: اجرای bot.py

چون پلن رایگان Render یه Worker داره، bot.py رو می‌تونید:

**گزینه ۱ — Worker جداگانه روی Railway (رایگان):**
```
railway.app → New Project → Deploy from GitHub
Environment Variables: BOT_TOKEN, WEB_APP_URL
Start command: python bot.py
```

**گزینه ۲ — روی همون Render Web Service ادغامش کنید:**
در `app/wsgi.py` بعد از setup Django یه thread برای bot بزنید (مثل bot.py فعلیتون)

**گزینه ۳ (توصیه شده برای شروع) — فقط BotFather:**
فقط از Menu Button استفاده کنید. نیازی به اجرای bot.py ندارید چون
forwarding پیام رو bot.py قدیمی شما (که الان روی Render هست) هندل می‌کنه.

---

## مرحله ۴ — ساخت superuser برای پنل ادمین

```bash
# در Render Shell یا locally:
python manage.py createsuperuser
# بعد به /admin-panel/ برید
```

---

## API Endpoints

| Method | URL | کار |
|--------|-----|-----|
| GET | `/api/dashboard/?tg_id=...` | لود اولیه همه داده‌ها |
| POST | `/api/notes/add/` | نوت جدید |
| DELETE | `/api/notes/<id>/delete/?tg_id=...` | حذف نوت |
| POST | `/api/vibe/update/` | آپدیت وایب |
| POST | `/api/todos/add/` | To-Do جدید |
| POST | `/api/todos/<id>/toggle/` | تیک/آنتیک |
| DELETE | `/api/todos/<id>/delete/?tg_id=...` | حذف |
| POST | `/api/routines/add/` | روتین جدید |
| POST | `/api/routines/<id>/check/` | تیک روتین امروز |
| POST | `/api/game/score/` | ثبت امتیاز بازی |
| GET | `/api/leaderboard/` | لیدربورد کامل |

---

## نکات مهم برای پلن رایگان Render

1. **سرور sleep می‌کنه:** بعد از ۱۵ دقیقه بی‌استفاده، Render سرور رو خاموش می‌کنه.
   اولین request کند میشه (cold start ~30 ثانیه). برای حل:
   - از [uptimerobot.com](https://uptimerobot.com) هر ۱۰ دقیقه ping بزنید (رایگانه)
   - Monitor → HTTP → URL رو `/` بزنید

2. **SQLite روی Render:** فایل `db.sqlite3` با هر deploy پاک میشه!
   برای نگه داشتن داده‌ها، یه Persistent Disk اضافه کنید ($7/ماه)
   یا از Render PostgreSQL رایگان استفاده کنید (توضیح در ادامه).

3. **PostgreSQL رایگان (توصیه برای production):**
   ```
   Render → New → PostgreSQL → Free plan
   آدرس Internal Database URL رو کپی کنید
   در settings.py:
   ```
   ```python
   import dj_database_url
   DATABASES = {'default': dj_database_url.config(default=os.environ.get('DATABASE_URL'))}
   ```
   ```
   requirements.txt: psycopg2-binary==2.9.9 و dj-database-url==2.1.0 اضافه کنید
   ```

---

## تست لوکال

```bash
git clone <repo>
cd couple-routine
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# مینی‌اپ: http://localhost:8000
# ادمین: http://localhost:8000/admin-panel/
# API تست: http://localhost:8000/api/dashboard/?tg_id=12345&name=علی
```

---

## ویژگی‌ها

| بخش | ویژگی‌ها |
|-----|---------|
| **وایب مودینگ** | ۱۵ وایب با ایموجی، نمایش وایب طرف مقابل در هدر |
| **دیلی نوت** | تگ احساسی، حذف، ۱۵ نوت آخر |
| **To-Do** | مشترک/شخصی، اولویت ۳ سطحی، نشان دادن اینکه چه کسی تیک زده |
| **روتین** | گرید ۲ستونه، تیک روزانه، undo، ایموجی |
| **بازی‌ها** | نبرد تپ (۵ ثانیه)، تست واکنش (ms)، بازی حافظه (۸ جفت) |
| **لیدربورد** | امتیاز کل، بهترین رکورد هر بازی |
