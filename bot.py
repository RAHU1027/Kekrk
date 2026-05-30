import os
import time
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
from utils import get_bin_details, check_card_with_braintree

# 1. Telegram Aur Database Setup
TOKEN = "8625009320:AAHphrFrjdBRRYBhdEE73PwsOlQ_YI9JjYc"
MONGO_URI = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Render automatically external URL provide karta hai (e.g., https://your-app.onrender.com)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client['tg_bot_db']
    users_collection = db['users']
    client.server_info()
except Exception:
    users_collection = None

# Core card processor function
async def process_card_check(card_string, user):
    start_time = time.time()
    try:
        cc_details = card_string.replace(" ", "").split("|")
        if len(cc_details) < 4:
            return "<b>❌ Format Error:</b> Use <code>CC|MM|YY|CVV</code>", None
            
        card_num, month, year, cvv = cc_details[0], cc_details[1], cc_details[2], cc_details[3]
        status_icon, response_text = check_card_with_braintree(card_num, month, year, cvv)
        bin_info = get_bin_details(card_num)
        execution_time = round(time.time() - start_time, 2)
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        
        # Design Layout
        designed_response = (
            f"↯  @kushal_99bot\n\n"
            f"• »  <b>Card</b> ⇾ <code>{card_num}|{month}|{year}|{cvv}</code>\n"
            f"• »  <b>Status</b> ⇾ {status_icon}\n"
            f"• »  <b>Response</b> ⇾ {response_text}\n\n"
            f"• »  <b>Issuer</b> ⇾ {bin_info['issuer']}\n"
            f"• »  <b>Info</b> ⇾ {bin_info['info']}\n"
            f"• »  <b>Country</b> ⇾ {bin_info['country']}\n\n"
            f"• »  <b>Gateway</b> ⇾ BRAINTREE AUTH\n"
            f"• »  <b>Request by</b> ⇾ {user_mention} [<code>{user.id}</code>]\n"
            f"• »  <b>Time</b> ⇾ {execution_time}s"
        )
        
        keyboard = [[InlineKeyboardButton("🔄 Re-Check Card", callback_data=f"recheck_{card_string}")]]
        return designed_response, InlineKeyboardMarkup(keyboard)
    except Exception as e:
        return f"⚠️ <b>System Error:</b> {str(e)}", None

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if users_collection:
        try:
            users_collection.update_one({"user_id": user.id}, {"$set": {"username": user.username, "first_name": user.first_name}}, upsert=True)
        except Exception:
            pass
    await update.message.reply_text(f"Welcome {user.first_name}! Use <code>/chk CC|MM|YY|CVV</code> to test cards.", parse_mode="HTML")

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("<b>⚠️ Usage:</b> <code>/chk 4658285013223866|01|26|838</code>", parse_mode="HTML")
        return
        
    status_msg = await update.message.reply_text("<code>Checking card, please wait...</code>", parse_mode="HTML")
    response_text, reply_markup = await process_card_check(context.args[0], user)
    await status_msg.edit_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer("Re-checking...")
    
    if query.data.startswith("recheck_"):
        card_string = query.data.replace("recheck_", "")
        await query.edit_message_text("<code>🔄 Re-checking status from gateway...</code>", parse_mode="HTML")
        response_text, reply_markup = await process_card_check(card_string, user)
        await query.edit_message_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

# Application Build
bot_app = Application.builder().token(TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("chk", chk_command))
bot_app.add_handler(CallbackQueryHandler(button_handler))

# 2. Flask Setup (Isi ke andar updates receive honge)
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot Webhook Gateway is Active!", 200

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    # Telegram se aane wale updates ko async loop me forward karna
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        # Run asynchronous process inside synchronous flask route
        asyncio.run(bot_app.process_update(update))
    return "OK", 200

def init_webhook():
    # Asynchronous initialization of Telegram bot inside Render
    asyncio.run(bot_app.initialize())
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/webhook"
        asyncio.run(bot_app.bot.set_webhook(url=webhook_url))
        print(f"✅ Webhook successfully set to: {webhook_url}")
    else:
        print("⚠️ Warning: RENDER_EXTERNAL_URL missing, running in default web mode.")

if __name__ == "__main__":
    # Webhook registry configure karein
    init_webhook()
    
    # Flask application start (Gunicorn/Render ready port binding)
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
