import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message

app = Client("megabot",
             api_id=int(os.getenv("API_ID")),
             api_hash=os.getenv("API_HASH"),
             bot_token=os.getenv("BOT_TOKEN"))

@app.on_message(filters.private)
async def catch_all(client, msg: Message):
    print(f"📩 Received private message from {msg.from_user.id}: {msg.text}")
    await msg.reply("✅ Hello from test bot!")

async def main():
    await app.start()
    print("✅ Bot started")
    await asyncio.Event().wait()

asyncio.run(main())
