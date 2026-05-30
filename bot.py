import os
import time
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
from utils import get_bin_details, check_card_with_braintree

# 1. Flask Web Server Logic (For Render Port Binding)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Live and Running 24/7!"

def run_flask():
    # Render automatically passes PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 2. Telegram Bot Configuration
TOKEN = "8625009320:AAHphrFrjdBRRYBhdEE73PwsOlQ_YI9JjYc"
MONGO_URI = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    db = client['tg_bot_db']
    users_collection = db['users']
except Exception:
    users_collection = None

# Core card processor function (Dono command aur button click ke liye common)
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
        
        # Aapka custom design layout
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
        
        # Re-check inline button attach karna (Isse user click karke re-deploy check kar sakta hai)
        keyboard = [[InlineKeyboardButton("🔄 Re-Check Card", callback_data=f"recheck_{card_string}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return designed_response, reply_markup
    except Exception as e:
        return f"⚠️ <b>System Error:</b> {str(e)}", None

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if users_collection:
        users_collection.update_one({"user_id": user.id}, {"$set": {"username": user.username, "first_name": user.first_name}}, upsert=True)
    await update.message.reply_text(f"Welcome {user.first_name}! Use <code>/chk CC|MM|YY|CVV</code> to test cards.", parse_mode="HTML")

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("<b>⚠️ Usage:</b> <code>/chk 4658285013223866|01|26|838</code>", parse_mode="HTML")
        return
        
    status_msg = await update.message.reply_text("<code>Checking card, please wait...</code>", parse_mode="HTML")
    response_text, reply_markup = await process_card_check(context.args[0], user)
    await status_msg.edit_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

# Callback Handler for Re-checking Button
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer("Re-triggering Gateway Check...")
    
    # Callback data se card nikalna
    if query.data.startswith("recheck_"):
        card_string = query.data.replace("recheck_", "")
        await query.edit_message_text("<code>🔄 Re-deploying request... Fetching live status...</code>", parse_mode="HTML")
        response_text, reply_markup = await process_card_check(card_string, user)
        await query.edit_message_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

def main():
    # Run Flask in a separate thread for Render port survival
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram Bot Polling
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("chk", chk_command))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Web Server + Bot Application started successfully!")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
