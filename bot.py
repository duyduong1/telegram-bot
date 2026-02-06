-- coding: utf-8 --

import logging
import random
import json
import time
import os
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6204301614
DATA_FILE = "data.json"
QR_IMAGE = "qr.jpg"

ORDER_COOLDOWN = 300
ORDER_TIMEOUT = 300
SPAM_LIMIT_10S = 5
AUTO_BAN_LIMIT = 10

if not TOKEN:
print("BOT_TOKEN cha c thit lp")
exit()

logging.basicConfig(level=logging.INFO)

def load_data():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, "r", encoding="utf-8") as f:
return json.load(f)
return {
"stock": {
"lv7_fb": 0,
"lv7_gg": 0,
"lv15_fb": 0,
"lv15_gg": 0
},
"banned": {},
"orders": {},
"users": []
}

data = load_data()

def save_data():
with open(DATA_FILE, "w", encoding="utf-8") as f:
json.dump(data, f, indent=4, ensure_ascii=False)

user_message_log = {}
user_spam_count = {}
user_last_order_time = {}

async def check_ban(update):
uid = str(update.effective_user.id)
if uid in data["banned"]:
if time.time() - data["banned"][uid] > 86400:
del data["banned"][uid]
save_data()
return False
if update.message:
await update.message.reply_text("Ban 24h do spam.")
elif update.callback_query:
await update.callback_query.answer("Ban 24h do spam.", show_alert=True)
return True
return False

async def anti_spam(update):
if not update.message:
return False

uid = str(update.effective_user.id)
now = time.time()

if uid not in user_message_log:
    user_message_log[uid] = []
    user_spam_count[uid] = 0

user_message_log[uid] = [t for t in user_message_log[uid] if now - t < 10]
user_message_log[uid].append(now)

if len(user_message_log[uid]) > SPAM_LIMIT_10S:
    user_spam_count[uid] += 1
    if user_spam_count[uid] >= AUTO_BAN_LIMIT:
        data["banned"][uid] = time.time()
        save_data()
        await update.message.reply_text("Spam quá nhiu. Ban 24h.")
        return True
    await update.message.reply_text("Spam ít thôi.")
    return True
return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
if await check_ban(update):
return
if await anti_spam(update):
return

uid = str(update.effective_user.id)
if uid not in data["users"]:
    data["users"].append(uid)
    save_data()

keyboard = [[
    InlineKeyboardButton("Acc Lv7 - 7000", callback_data="select_lv7"),
    InlineKeyboardButton("Acc Lv15 - 10000", callback_data="select_lv15")
]]

await update.message.reply_text(
    "SHOP ACC FREE FIRE\nChn cp :",
    reply_markup=InlineKeyboardMarkup(keyboard)
)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
if await check_ban(update):
return

q = update.callback_query
await q.answer()
uid = str(q.from_user.id)
action = q.data
now = time.time()

if action.startswith("buy_"):
    if uid in user_last_order_time:
        if now - user_last_order_time[uid] < ORDER_COOLDOWN:
            con_lai = int(ORDER_COOLDOWN - (now - user_last_order_time[uid]))
            await q.answer(f"Doi {con_lai}s de tao don moi", show_alert=True)
            return
    user_last_order_time[uid] = now

if action == "select_lv7":
    keyboard = [[
        InlineKeyboardButton("Facebook", callback_data="buy_lv7_fb"),
        InlineKeyboardButton("Google", callback_data="buy_lv7_gg")
    ]]
    await q.message.edit_text("LV7 - 7000", reply_markup=InlineKeyboardMarkup(keyboard))

elif action == "select_lv15":
    keyboard = [[
        InlineKeyboardButton("Facebook", callback_data="buy_lv15_fb"),
        InlineKeyboardButton("Google", callback_data="buy_lv15_gg")
    ]]
    await q.message.edit_text("LV15 - 10000", reply_markup=InlineKeyboardMarkup(keyboard))

elif action.startswith("buy_"):
    p_type = action.replace("buy_", "")
    stock = data["stock"].get(p_type, 0)

    if stock <= 0:
        await q.answer("Het hang", show_alert=True)
        return

    order_id = str(random.randint(1000000, 9999999))
    data["orders"][uid] = {
        "type": p_type,
        "id": order_id,
        "time": time.time()
    }
    save_data()

    caption = f"DON HANG\n\nLoai: {p_type}\nID: {order_id}\nGui bill sau khi chuyen khoan"

    with open(QR_IMAGE, "rb") as photo:
        await context.bot.send_photo(chat_id=uid, photo=photo, caption=caption)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
if await check_ban(update):
return

uid = str(update.effective_user.id)
order = data["orders"].get(uid)
if not order:
    return

await context.bot.forward_message(ADMIN_ID, uid, update.message.message_id)
await update.message.reply_text("Da gui bill. Cho admin duyet.")

async def gui(update: Update, context: ContextTypes.DEFAULT_TYPE):
if update.effective_user.id != ADMIN_ID:
return
try:
args = " ".join(context.args).split("|")
uid = args[0].strip()
gmail = args[1].strip()
password = args[2].strip()

    if uid in data["orders"]:
        p_type = data["orders"][uid]["type"]

        if data["stock"][p_type] <= 0:
            await update.message.reply_text("Het hang")
            return

        data["stock"][p_type] -= 1
        del data["orders"][uid]
        save_data()

        await context.bot.send_message(uid, f"Thanh cong\nGmail: {gmail}\nPass: {password}")
        await update.message.reply_text("Da giao acc")
except:
    await update.message.reply_text("Dung: /gui ID|gmail|pass")

async def auto_cancel(context: ContextTypes.DEFAULT_TYPE):
now = time.time()
expired = []

for uid, order in list(data["orders"].items()):
    if now - order["time"] > ORDER_TIMEOUT:
        expired.append(uid)

for uid in expired:
    try:
        await context.bot.send_message(uid, "Don tu huy sau 5 phut")
    except:
        pass
    del data["orders"][uid]

if expired:
    save_data()

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("gui", gui))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.job_queue.run_repeating(auto_cancel, interval=60, first=10)

flask_app = Flask(name)

@flask_app.route("/")
def home():
return "Bot dang chay"

@flask_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
update = Update.de_json(request.get_json(force=True), app.bot)
asyncio.run(app.process_update(update))
return "ok"

async def main():
await app.initialize()
await app.bot.set_webhook(os.environ.get("RENDER_EXTERNAL_URL") + f"/webhook/{TOKEN}")

asyncio.run(main())

port = int(os.environ.get("PORT", 10000))
flask_app.run(host="0.0.0.0", port=port)