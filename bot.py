import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand

# TOKEN ko yahan paste karo (Revoke zaroor kar lena)
TOKEN = "8921575955:AAF8z-GI9xffH-j7E0LV2ai8xEcS36cCcmY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Memory Storage (Production mein yahan MongoDB jodenge)
user_db = {}

async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="start", description="Welcome & About"),
        BotCommand(command="generate", description="Create new email"),
        BotCommand(command="id", description="View account stats"),
        BotCommand(command="delete", description="Delete active email"),
        BotCommand(command="transfer", description="Transfer data")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        "✨ *Welcome to KUSHAL MAIL BOT* ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ *Trusted & Secure Service*\n"
        "🛡️ *100% Privacy (No Data Leaks)*\n"
        "⚡ *24/7 Active Infrastructure*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Thanks for joining the most secure mail platform. "
        "We ensure your privacy is top-tier. Your data stays safe.\n\n"
        "🚀 *Commands:* Use /generate to start your journey!\n\n"
        "🙏 *Thanks for your support!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("generate"))
async def generate_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_db:
        user_db[user_id] = {"count": 0, "active_mail": None}
    
    user_db[user_id]["count"] += 1
    email = f"kushal_{user_id}_{user_db[user_id]['count']}@kushalmail.com"
    user_db[user_id]["active_mail"] = email
    
    await message.answer(f"✅ *Email Ready for All Platforms*:\n\n`{email}`\n\nWaiting for OTP/Code...", parse_mode="Markdown")

@dp.message(Command("id"))
async def id_cmd(message: types.Message):
    user_id = message.from_user.id
    data = user_db.get(user_id, {"count": 0, "active_mail": "None"})
    await message.answer(
        f"👤 *Account Statistics*\n\n"
        f"📊 Total Emails Generated: `{data['count']}`\n"
        f"📧 Current Active Mail: `{data['active_mail']}`", 
        parse_mode="Markdown"
    )

@dp.message(Command("delete"))
async def delete_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_db:
        user_db[user_id]["active_mail"] = None
        await message.answer("🗑️ *Active email deleted successfully.*")
    else:
        await message.answer("❌ *No active email found to delete.*")

@dp.message(Command("transfer"))
async def transfer_cmd(message: types.Message):
    await message.answer("🔄 *Migration System*\n\nEnter your migration code from your previous provider to sync your history.")

async def main():
    await set_main_menu(bot)
    print("Kushal Bot is online and ready...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
