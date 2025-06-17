
import asyncio
import os
import re
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums, idle
from pyrogram.types import Message
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7868250691
LOG_FILE = "verified_users.txt"

print("🔧 [DEBUG] ENV Loaded:")
print("API_ID:", API_ID)
print("API_HASH:", API_HASH)
print("BOT_TOKEN:", "HIDDEN" if BOT_TOKEN else "None")

app = Client("megabot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

frees = {}
verifying = {}
approved_users = set()
verification_map = {}

def parse_time(text):
    match = re.match(r"(\d+)([dhm])", text)
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return {
        'd': timedelta(days=value),
        'h': timedelta(hours=value),
        'm': timedelta(minutes=value)
    }.get(unit, None)

@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    print(f"[DEBUG] /start received from {msg.from_user.id}")
    print(f"[DEBUG] Message: {msg.text}")
    await msg.reply_text(f"Welcome to Gamer Grindhouse Network Verification Bot {msg.from_user.mention}! 🎮\n\nClick /verify to continue ❤️")

@app.on_message(filters.command("verify") & filters.private)
async def verify(_, msg: Message):
    username = msg.from_user.username or msg.from_user.first_name
    verifying[msg.from_user.id] = {'video': None, 'photo': None}
    await msg.reply_text(
        f"It's time to verify {username}!\n\n🎥 Please long-press the mic to record a live video saying today's date, your username, and 'verifying for Gamer Grindhouse'.\n📸 Then send a screenshot of your ID or website profile."
    )
    await msg.reply_text("Checking fedban status with @MissRose_Bot... 👮‍♀️")
    await app.send_message("MissRose_bot", f"/fbanstat @{username}")
    await asyncio.sleep(2)

@app.on_message(filters.private & filters.video_note)
async def video_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]['video'] = msg
        await msg.reply("✅ Video received! Now please send your ID or website screenshot.")

@app.on_message(filters.private & filters.photo)
async def photo_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]['photo'] = msg
        data = verifying[msg.from_user.id]
        await msg.reply("🎉 Your verification has been sent to an admin!")

        video_msg = data['video']
        photo_msg = data['photo']

        fwd_video = await app.forward_messages(OWNER_ID, msg.chat.id, video_msg.id)
        fwd_photo = await app.forward_messages(OWNER_ID, msg.chat.id, photo_msg.id)

        verification_map[fwd_video.id] = msg.from_user.id
        verification_map[fwd_photo.id] = msg.from_user.id

        await app.send_message(OWNER_ID, f"⚠️ Don't forget to check @{msg.from_user.username or msg.from_user.first_name}'s fedbans with @MissRose_Bot!")

@app.on_message(filters.private & filters.reply & filters.user(OWNER_ID))
async def approve_or_reject(_, msg: Message):
    replied_msg = msg.reply_to_message
    user_id = verification_map.get(replied_msg.id)

    if not user_id:
        return await msg.reply("❌ Couldn’t match this verification to a user. Please ask them to restart.")

    if msg.text.lower().startswith("approve"):
        if user_id and user_id != "TestLunaFoxx":
            approved_users.add(user_id)
            with open(LOG_FILE, "a") as f:
                f.write(f"{user_id}\n")
        await app.send_message(user_id, "✅ You're approved! Welcome to the network!\nClick to join: https://t.me/+Rp4xgxUFrMdjZTZk")

    elif msg.text.lower().startswith("reject"):
        reason = msg.text.split(" ", 1)[1] if " " in msg.text else "No reason provided"
        await app.send_message(user_id, f"❌ Verification rejected: {reason}\nTry again with /verify or contact @The_LunaFoxx.")

@app.on_message(filters.command("free") & filters.group)
async def free(_, msg: Message):
    if msg.from_user.id != OWNER_ID and not msg.from_user.is_chat_admin():
        return
    if len(msg.command) < 3:
        await msg.reply("Usage: /free @username 3d")
        return
    user_mention = msg.command[1]
    duration = msg.command[2]

    try:
        target = await app.get_users(msg.command[1])
    except:
        await msg.reply("Couldn't find that user.")
        return

    if target.username == "TestLunaFoxx":
        return

    tdelta = parse_time(duration)
    if tdelta is None and duration != "0":
        await msg.reply("Invalid time format. Use 1d, 2h, 30m, or 0 for infinite.")
        return

    until = None if duration == "0" else datetime.utcnow() + tdelta
    frees[target.id] = until
    await msg.reply(f"✅ {user_mention} has been freed {'forever' if until is None else f'until {until}'}")

@app.on_message(filters.command("unfree") & filters.group)
async def unfree(_, msg: Message):
    if msg.from_user.id != OWNER_ID and not msg.from_user.is_chat_admin():
        return
    if len(msg.command) < 2:
        await msg.reply("Usage: /unfree @username")
        return
    try:
        target = await app.get_users(msg.command[1])
    except:
        await msg.reply("Couldn't find that user.")
        return

    if target.id in frees:
        del frees[target.id]
        await msg.reply(f"{target.mention} has been unfreed.")

@app.on_message(filters.command("unfree_all") & filters.group)
async def unfree_all(_, msg: Message):
    if msg.from_user.id != OWNER_ID and not msg.from_user.is_chat_admin():
        return
    for uid in list(frees.keys()):
        del frees[uid]
    await msg.reply("🧹 All users have been unfree’d.")

@app.on_message(filters.group)
async def auto_delete(_, msg: Message):
    if msg.from_user.id in frees:
        until = frees[msg.from_user.id]
        if until and datetime.utcnow() > until:
            del frees[msg.from_user.id]
        else:
            try:
                await msg.delete()
            except:
                pass

@app.on_chat_member_updated()
async def on_new_group(_, event):
    if event.new_chat_member.user.id == (await app.get_me()).id:
        chat_id = event.chat.id
        async for member in app.get_chat_members(chat_id):
            frees[member.user.id] = None
        await app.send_message(chat_id, "Bot has joined! All users unfree’d for now!")

keep_alive()

print("🤖 MegaBot is alive and slaying!")
app.run()
