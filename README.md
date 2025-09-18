# Kvitkova Telegram Booking Bot (Capacity per Slot)

This is a **ready-to-deploy** Telegram bot for booking delivery time slots with **capacity** (e.g., up to 3 clients per hour).
Tech: Python, FastAPI (webhook), aiogram v3, SQLite. Works great on Render.com.

---

## ✨ What clients see (super simple)
1. Tap your link → bot opens.
2. Pick a day.
3. Pick a time (it shows **left seats**, e.g., `12:00 (2)`).
4. Confirm. Done.

They also get a message to reschedule/cancel if needed.

---

## 🧰 What you need
- Telegram account
- Render.com account (free tier is fine)
- GitHub account (to host the repository)

---

## 🚀 Step‑by‑step (non‑developer friendly)

### 1) Create a Telegram Bot
1. Open Telegram → search **@BotFather**.
2. Send `/newbot` and follow steps.
3. Copy the **Bot Token** (looks like `123456:ABC-DEF...`). Keep it safe.

### 2) Prepare the repository (GitHub via browser, no coding)
1. Go to https://github.com → Sign in → **New repository** → Name: `kvitkova-bot` → Create.
2. Click **Add file → Upload files**, then **drag-and-drop** all files from the unzipped folder you downloaded (see below).
3. Commit (save). Done.

*(If you don’t know how to unzip: open the ZIP file, click “Extract All…”, choose a folder, then upload the extracted files.)*

### 3) Deploy on Render.com (free & easy)
1. Create an account at https://render.com → **New +** → **Web Service**.
2. Connect your GitHub, choose `kvitkova-bot` repo.
3. Settings:
   - **Environment:** `Python 3`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Click **Create Web Service** and wait until it deploys the first time.
5. After deploy, copy your **Public URL**, e.g. `https://kvitkova-bot.onrender.com`.

### 4) Add Environment Variables on Render
Go to your service → **Environment** → **Add Environment Variable**:
- `BOT_TOKEN` = (paste your BotFather token)
- `PUBLIC_URL` = your Render URL, e.g. `https://kvitkova-bot.onrender.com`
- `WEBHOOK_SECRET` = any hard string, e.g. `mysecret12345`
- `ADMIN_ID` = your personal Telegram numeric ID (get it by sending `/whoami` to the bot once it’s running; you can set a placeholder for now like `0` and update later)

Click **Save Changes** and **Redeploy**.

> On startup, the app automatically sets Telegram webhook to:
> `PUBLIC_URL` + `/webhook/` + `WEBHOOK_SECRET`

### 5) Start the bot
1. In Telegram, open your bot (the @username you created).
2. Type `/start` or tap the **Start** button.
3. You’ll see available days and slots. If empty, add slots (next step).

### 6) Add delivery slots (admin command)
Only **ADMIN_ID** can add slots.

Format:
```
/addslot 2025-09-21 12:00 13:00 3 solomyanka
```
That means:
- Date: `2025-09-21`
- From: `12:00`
- To: `13:00`
- Capacity: `3` clients
- Zone: `solomyanka` (optional text; can be `-` to skip)

**Examples:**
```
/addslot 2025-09-21 10:00 11:00 3 center
/addslot 2025-09-21 11:00 12:00 3 center
/addslot 2025-09-21 12:00 13:00 3 center
```

### 7) Optional: Cancel/Move bookings (client)
- Clients can press **“Перенести/Скасувати”** from their confirmation message.
- Admin can also cancel client’s booking via `/cancel <booking_id>` (shown in admin notifications).

---

## 🧩 How it works
- **Slots** table has `capacity` and `booked_count`.
- When a client confirms, bot **locks** row (SQLite transaction) and **increments** booked count atomically.
- Keyboard shows `time (left)` — e.g., `12:00 (2)`.
- Slots disappear when full.

---

## 🔒 Admin & Security
- Only `ADMIN_ID` can run admin commands (`/addslot`, `/slots`, `/cancel`, `/broadcast`).
- Webhook secret ensures only Telegram hits your endpoint.
- Don’t share your `BOT_TOKEN`.

---

## 🛠 Local run (optional)
- Create `.env` from `.env.example`
- Install Python 3.11+, then:
```
pip install -r requirements.txt
python -m uvicorn main:app --reload
```
- Use a tool like **ngrok** to expose your local URL and set `PUBLIC_URL` to that temporary URL if you want webhooks locally.

---

## 📦 Files
- `main.py` — FastAPI + aiogram app
- `db.py` — SQLite helpers and migrations
- `requirements.txt` — dependencies
- `.env.example` — example environment variables
- `README.md` — this guide

---

## ❓ FAQ
**Q: How do I get my Telegram numeric ID for ADMIN_ID?**
A: After the bot runs, send `/whoami` to the bot. It will reply with your ID. Then set that number in Render’s Environment and redeploy.

**Q: Timezone?**
Times are stored as text (e.g., `12:00`). For Kyiv, simply create slots in **Europe/Kyiv** time; clients see times exactly as you write them.

**Q: Multiple admins?**
Set `ADMIN_ID` to a comma-separated list (e.g., `123,456`).

**Q: CSV import?**
For MVP we use `/addslot`. If you want CSV import later, we can add it.