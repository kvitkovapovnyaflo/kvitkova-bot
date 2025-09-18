
import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from db import query, execute, tx
from aiogram.client.default import DefaultBotProperties  

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0")

ADMIN_IDS = set()
for part in ADMIN_ID_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        ADMIN_IDS.add(int(part))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

app = FastAPI()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or (len(ADMIN_IDS) == 0 and user_id == 0)

def fmt_slot_row(row):
    sid, date, start, end, zone, cap, booked = row
    left = cap - booked
    zone_txt = f" • {zone}" if zone and zone != "-" else ""
    return f"#{sid} {date} {start}-{end}{zone_txt} • {booked}/{cap} ({left} left)"

@dp.message(CommandStart())
async def start(m: types.Message):
    kb = InlineKeyboardBuilder()
    days = query("SELECT DISTINCT date FROM slots WHERE booked_count < capacity ORDER BY date")
    if not days:
        await m.answer("Поки немає доступних слотів 🌸 Спробуй пізніше.")
        return
    for (d,) in days:
        kb.button(text=d, callback_data=f"day:{d}")
    await m.answer("Обери день доставки 🌸", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("day:"))
async def choose_time(c: types.CallbackQuery):
    day = c.data.split(":")[1]
    rows = query("SELECT id, time_start, time_end, capacity, booked_count FROM slots WHERE date=? ORDER BY time_start", (day,))
    kb = InlineKeyboardBuilder()
    for sid, t_start, t_end, cap, booked in rows:
        left = cap - booked
        label = f"{t_start} ({left})"
        if left > 0:
            kb.button(text=label, callback_data=f"slot:{sid}")
        else:
            kb.button(text=f"{t_start} (0)", callback_data="noop")
    kb.button(text="« Інший день", callback_data="back:days")
    await c.message.edit_text(f"Доступні слоти на {day}:", reply_markup=kb.as_markup())
    await c.answer()

@dp.callback_query(F.data == "back:days")
async def back_days(c: types.CallbackQuery):
    await start(c.message)
    await c.answer()

@dp.callback_query(F.data.startswith("slot:"))
async def confirm_slot(c: types.CallbackQuery):
    sid = int(c.data.split(":")[1])
    row = query("SELECT date, time_start, time_end, capacity, booked_count FROM slots WHERE id=?", (sid,))
    if not row:
        await c.answer("Слот недоступний", show_alert=True); return
    date, t_start, t_end, cap, booked = row[0]
    left = cap - booked
    if left <= 0:
        await c.answer("Вже зайнято 😔", show_alert=True); return
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Підтвердити", callback_data=f"ok:{sid}")
    kb.button(text="↩️ Інший час", callback_data=f"day:{date}")
    await c.message.edit_text(f"Підтверджуєш {date} о {t_start}?", reply_markup=kb.as_markup())
    await c.answer()

@dp.callback_query(F.data.startswith("ok:"))
async def finalize(c: types.CallbackQuery):
    sid = int(c.data.split(":")[1])
    uid = c.from_user.id
    try:
        with tx() as _conn:
            row = _conn.execute("SELECT capacity, booked_count FROM slots WHERE id=?", (sid,)).fetchone()
            if not row:
                return await c.answer("Слот недоступний", show_alert=True)
            cap, booked = row
            if booked >= cap:
                return await c.answer("Вже зайнято 😔", show_alert=True)
            _conn.execute("INSERT INTO bookings(user_id, slot_id, status) VALUES(?,?,?)", (str(uid), sid, "confirmed"))
            _conn.execute("UPDATE slots SET booked_count=booked_count+1 WHERE id=?", (sid,))
        await c.message.edit_text("Заброньовано! 🎉 За 30–60 хв до приїзду напишемо.")
        await c.answer()
    except Exception as e:
        await c.answer("Помилка бронювання. Спробуй ще раз.", show_alert=True)

@dp.message(Command(commands=["whoami"]))
async def whoami(m: types.Message):
    await m.answer(f"Ваш Telegram ID: <b>{m.from_user.id}</b>")

@dp.message(Command(commands=["addslot"]))
async def addslot(m: types.Message):
    if not is_admin(m.from_user.id):
        await m.answer("Тільки для адміністратора."); return
    args = m.text.split()
    if len(args) < 5:
        await m.answer("Формат: /addslot 2025-09-21 12:00 13:00 3 [zone]"); return
    _, date, t_start, t_end, cap, *zone = args
    zone = zone[0] if zone else "-"
    try:
        cap = int(cap)
    except:
        await m.answer("Capacity має бути числом."); return
    sid = execute(
        "INSERT INTO slots(date, time_start, time_end, zone, capacity, booked_count) VALUES(?,?,?,?,?,0)",
        (date, t_start, t_end, zone, cap)
    )
    await m.answer(f"Додано слот #{sid}: {date} {t_start}-{t_end} • {zone} • capacity={cap}")

@dp.message(Command(commands=["slots"]))
async def list_slots(m: types.Message):
    if not is_admin(m.from_user.id):
        await m.answer("Тільки для адміністратора."); return
    rows = query("SELECT id, date, time_start, time_end, zone, capacity, booked_count FROM slots ORDER BY date, time_start")
    if not rows:
        await m.answer("Слотів ще немає."); return
    text = "\n".join(fmt_slot_row(r) for r in rows[:100])
    await m.answer(text)

@dp.message(Command(commands=["cancel"]))
async def cancel_booking(m: types.Message):
    if not is_admin(m.from_user.id):
        await m.answer("Тільки для адміністратора."); return
    args = m.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await m.answer("Формат: /cancel 123"); return
    bid = int(args[1])
    row = query("SELECT slot_id, status FROM bookings WHERE id=?", (bid,))
    if not row:
        await m.answer("Бронювання не знайдено"); return
    slot_id, status = row[0]
    if status != "confirmed":
        await m.answer("Це бронювання вже скасовано."); return
    with tx() as _conn:
        _conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (bid,))
        _conn.execute("UPDATE slots SET booked_count=booked_count-1 WHERE id=? AND booked_count>0", (slot_id,))
    await m.answer(f"Скасовано бронювання #{bid}")

@app.get("/")
async def root():
    return {"ok": True, "service": "kvitkova-bot"}

@app.post(f"/webhook/{WEBHOOK_SECRET}")
async def webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = await request.body()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)

@app.on_event("startup")
async def on_startup():
    if PUBLIC_URL:
        url = f"{PUBLIC_URL}/webhook/{WEBHOOK_SECRET}"
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass
        await bot.set_webhook(url)
