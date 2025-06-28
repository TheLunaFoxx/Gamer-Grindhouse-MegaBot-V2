import os
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

print("🔧 [DEBUG] TEST BOT LAUNCH")
print("API_ID:", API_ID)
print("BOT_TOKEN:", "HIDDEN" if BOT_TOKEN else "Missing")

app = Client("testbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.private)
async def reply_debug(_, msg: Message):
    print(f"[TEST DEBUG] Received private msg: {msg.text} from {msg.from_user.id}")
    await msg.reply("✅ This is a test bot. You're good!")

app.run()
