import os
import time
import asyncio
import random
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from pymongo import MongoClient
from utils import get_bin_details, check_card_with_braintree, generate_cards_logic

# 1. Configuration Tokens
TOKEN = "8625009320:AAHphrFrjdBRRYBhdEE73PwsOlQ_YI9JjYc"
MONGO_URI = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client['tg_bot_db']
    users_collection = db['users']
except Exception:
    users_collection = None

bot_app = Application.builder().token(TOKEN).build()

# Core Card Checker
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

# Welcome Command
async def start(update: Update, context):
    user = update.effective_user
    if users_collection:
        try: users_collection.update_one({"user_id": user.id}, {"$set": {"username": user.username, "first_name": user.first_name}}, upsert=True)
        except Exception: pass
            
    username_text = f"@{user.username}" if user.username else "No Username"
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    
    welcome_text = (
        f"👋 <b>Welcome, {user_mention}!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• » <b>User Info:</b> {user_mention}\n"
        f"• » <b>Username:</b> {username_text}\n"
        f"• » <b>User ID:</b> <code>{user.id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ <b>Commands:</b>\n"
        f"➡️ <code>/chk CC|MM|YY|CVV</code> - Card Checker\n"
        f"➡️ <code>/gen BIN</code> - Card Generator (With Live Country)"
    )
    try:
        user_profile_photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if user_profile_photos.total_count > 0:
            photo_id = user_profile_photos.photos[0][-1].file_id
            await update.message.reply_photo(photo=photo_id, caption=welcome_text, parse_mode="HTML")
        else:
            await update.message.reply_text(welcome_text, parse_mode="HTML")
    except Exception:
        await update.message.reply_text(welcome_text, parse_mode="HTML")

# Upgraded /gen Command with Live BIN Details & Accurate Expiries
async def gen_command(update: Update, context):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("<b>⚠️ Usage:</b> <code>/gen 465828</code>", parse_mode="HTML")
        return
        
    bin_input = context.args[0][:6]
    if len(bin_input) < 6:
        await update.message.reply_text("<b>❌ Error:</b> BIN kam se kam 6 digits ka hona chahiye.", parse_mode="HTML")
        return
        
    status_msg = await update.message.reply_text("<code>Generating valid cards & fetching live country data...</code>", parse_mode="HTML")
    
    # Live Country aur Info extract karna generator ke liye
    bin_info = get_bin_details(bin_input)
    cards = generate_cards_logic(bin_input, amount=10)
    
    output = (
        f"↯  <b>@kushal_99bot Generator</b>\n\n"
        f"• »  <b>BIN:</b> <code>{bin_input}</code>\n"
        f"• »  <b>Issuer:</b> {bin_info['issuer']}\n"
        f"• »  <b>Country:</b> {bin_info['country']}\n"
        f"• »  <b>Info:</b> {bin_info['info']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    
    # 2026 ke according logical realistic expiry append karna
    for c in cards:
        month = str(random.randint(1, 12)).zfill(2)
        year = str(random.randint(26, 32)) # Realistic expiry range up to 2032
        cvv = str(random.randint(100, 999))
        output += f"• » <code>{c}|{month}|{year}|{cvv}</code>\n"
        
    output += f"━━━━━━━━━━━━━━━━━━\n• » <b>Generated by:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>"
    
    await status_msg.edit_text(output, parse_mode="HTML")

# Checker command
async def chk_command(update: Update, context):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("<b>⚠️ Usage:</b> <code>/chk 4658285013223866|01|26|838</code>", parse_mode="HTML")
        return
    status_msg = await update.message.reply_text("<code>Checking card, please wait...</code>", parse_mode="HTML")
    response_text, reply_markup = await process_card_check(context.args[0], user)
    await status_msg.edit_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

async def button_handler(update: Update, context):
    query = update.callback_query
    user = query.from_user
    await query.answer("Re-checking...")
    if query.data.startswith("recheck_"):
        card_string = query.data.replace("recheck_", "")
        await query.edit_message_text("<code>🔄 Re-checking status from gateway...</code>", parse_mode="HTML")
        response_text, reply_markup = await process_card_check(card_string, user)
        await query.edit_message_text(response_text, parse_mode="HTML", reply_markup=reply_markup)

# Register Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("gen", gen_command))
bot_app.add_handler(CommandHandler("chk", chk_command))
bot_app.add_handler(CallbackQueryHandler(button_handler))

# Flask Webhook Setup
flask_app = Flask(__name__)

def initialize_bot_engine():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.initialize())
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        loop.run_until_complete(bot_app.bot.set_webhook(url=webhook_url))

@flask_app.route('/')
def home(): return "Bot status: Online", 200

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, bot_app.bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.process_update(update))
    return "OK", 200

if __name__ == "__main__":
    initialize_bot_engine()
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
