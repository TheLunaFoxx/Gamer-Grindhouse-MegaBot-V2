import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.types import Message
from keep_alive import keep_alive
from pyrogram.enums import ChatMemberStatus

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

BOT_USER = None

async def set_bot_user():
    global BOT_USER
    me = await app.get_me()
    BOT_USER = me.id

# Utility function to parse duration like 3d, 4h, 30m
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
    print(f"[DEBUG] /start command received from: {msg.from_user.id}")
    try:
        await msg.reply_text(
            f"Welcome to <b>Gamer Grindhouse Network Verification Bot {msg.from_user.mention}!</b> 🎮\n\nClick /verify to continue ❤️", parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"[ERROR] Failed to send /start message: {e}")

@app.on_message(filters.command("verify") & filters.private)
async def verify(_, msg: Message):
    username = msg.from_user.username or msg.from_user.first_name
    verifying[msg.from_user.id] = {'video': None, 'photo': None}
    await msg.reply_text(f"It's time to verify {username}!\n\n🎥 Please click the mic in the bottom right corner to change it to a camera. Then, <b>long-press the camera</b> to record a live video saying <b>today's date, your username, and 'verifying for Gamer Grindhouse'.</b>\n📸 Then send a <b>screenshot of your ID</b> or <b>18+ website profile <i>(Onlyfans, Fansly etc. Make sure your username is visible!)</i></b>.\n\nPlease send them <b>in this order</b> to ensure your information is sent to the owner correctly! ❤️", parse_mode=ParseMode.HTML)
    await msg.reply_text("<b>Checking fedban status with @MissRose_Bot... 👮‍♀️</b>", parse_mode=ParseMode.HTML)
    await app.send_message("MissRose_bot", f"/fbanstat @{username}")
    await asyncio.sleep(2)

@app.on_message(filters.private & filters.video_note)
async def video_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]['video'] = msg
        await msg.reply("✅ Video received! Now please send your <b>ID</b> or <b>website screenshot!</b>", parse_mode=ParseMode.HTML)

@app.on_message(filters.private & filters.photo)
async def photo_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]['photo'] = msg
        data = verifying[msg.from_user.id]
        await msg.reply("🎉 Your verification has been sent to the owner, and a decision will be made <b><i>ASAP!</i></b>", parse_mode=ParseMode.HTML)

        video_msg = data['video']
        photo_msg = data['photo']

        fwd_video = await app.forward_messages(OWNER_ID, msg.chat.id, video_msg.id)
        fwd_photo = await app.forward_messages(OWNER_ID, msg.chat.id, photo_msg.id)

        verification_map[fwd_video.id] = msg.from_user.id
        verification_map[fwd_photo.id] = msg.from_user.id

        await app.send_message(OWNER_ID, f"⚠️ Don’t forget to check @{msg.from_user.username or msg.from_user.first_name}'s fedbans!")

@app.on_message(filters.private & filters.reply & filters.user(OWNER_ID))
async def approve_or_reject(_, msg: Message):
    replied_msg = msg.reply_to_message
    user_id = verification_map.get(replied_msg.id)

    if not user_id:
        return await msg.reply("❌ <b>Couldn’t match this verification to a user.</b>\nPlease ask them to <b>restart</b>.", parse_mode=ParseMode.HTML)

    if msg.text.lower().startswith("approve"):
        if user_id != "TestLunaFoxx":
            approved_users.add(user_id)
            with open(LOG_FILE, "a") as f:
                f.write(f"{user_id}\n")
        await app.send_message(user_id, "✅ <b>You're approved!</b> Welcome to the network!\nClick below to join the network and groups 👇\n<b><u>https://t.me/addlist/mt_KC0gfZBkzMzk0</u></b>\n\nRules:\n✅ Please ensure you <b>complete your POP to unlock</b> within <b>24 hours</b> of joining the network,\n✅ <b><u>SFW flyers only</u></b>. This means <b>no <i>nips</i>, <i>bits</i> or <i>cracks</i></b> to be visible AT ALL (they can be <b>blurred</b>, don't worry!),\n✅ Do <b><u>NOT</u></b> message potential buyers first. If you are caught doing this, it will result in an <b>instant ban and fedban against your name</b>,\n✅ <b>Assistants</b> are allowed to complete POP on your behalf, but please direct them to myself (<u>@GamerGrindhouseMegaBot</u>) to <b>complete verification</b>!", parse_mode=ParseMode.HTML)

    elif msg.text.lower().startswith("reject"):
        reason = msg.text.split(" ", 1)[1] if " " in msg.text else "No reason provided"
        await app.send_message(user_id, f"❌ <b>Verification rejected:</b> {reason}\n<b>Try again</b> with /verify or contact @The_LunaFoxx if you're having any issues!", parse_mode=ParseMode.HTML)

@app.on_message(filters.command("free") & filters.group)
async def free(_, msg: Message):
    chat_member = await app.get_chat_member(msg.chat.id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return

    try:
        target = await app.get_users(msg.command[1])
    except:
        await msg.reply("❌ <b>Couldn't find that user.</b>", parse_mode=ParseMode.HTML)
        return

    tdelta = parse_time(msg.command[2])
    if tdelta is None and msg.command[2] != "0":
        await msg.reply("Invalid format. Use 1d, 2h, 30m or 0 for forever.")
        return

    until = None if msg.command[2] == "0" else datetime.now(timezone.utc) + tdelta
    frees[target.id] = until
    await msg.reply(f"✅ <b>{target.mention} has been free'd</b> {'forever' if until is None else f'until {until}'}", parse_mode=ParseMode.HTML)

@app.on_message(filters.command("unfree") & filters.group)
async def unfree(_, msg: Message):
    chat_member = await app.get_chat_member(msg.chat.id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return

    try:
        target = await app.get_users(msg.command[1])
    except:
        await msg.reply("❌ <b>Couldn't find that user.</b>", parse_mode=ParseMode.HTML)
        return

    if target.id in frees:
        del frees[target.id]
        await msg.reply(f"❌ <b>{target.mention} has been unfree'd.</b>", parse_mode=ParseMode.HTML)

@app.on_message(filters.command("unfree_all") & filters.group)
async def unfree_all(_, msg: Message):
    chat_member = await app.get_chat_member(msg.chat.id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return
    frees.clear()
    await msg.reply("🧹 <b>All users have been unfree'd.</b>", parse_mode=ParseMode.HTML)

@app.on_message(filters.group)
async def auto_delete(_, msg: Message):
    if msg.from_user.id in frees:
        until = frees[msg.from_user.id]
        if until and datetime.now(timezone.utc) > until:
            del frees[msg.from_user.id]
        else:
            try:
                await msg.delete()
            except: pass

@app.on_chat_member_updated()
async def on_chat_member_update(_, event):
    global BOT_USER
    user = event.new_chat_member.user
    chat_id = event.chat.id

    if user.id == BOT_USER:
        async for member in app.get_chat_members(chat_id):
            if member.user.is_bot or member.user.id == OWNER_ID or member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                continue
            frees[member.user.id] = None
        await app.send_message(chat_id, "<b>👋 Bot added to group. All non-admin users unfree'd by default.</b>", parse_mode=ParseMode.HTML)
    elif user.id != OWNER_ID and event.new_chat_member.status == ChatMemberStatus.MEMBER:
        member = await app.get_chat_member(chat_id, user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            frees[user.id] = None
            print(f"[DEBUG] New user {user.id} added to frees list")
            try:
                sent = await app.send_message(chat_id, f"❌ <b>{user.mention} has been unfree'd.</b> They must complete POP to post if they are a model!", parse_mode=ParseMode.HTML)
                await asyncio.sleep(30)
                await sent.delete()
            except:
                pass

@app.on_message(filters.private)
async def catch_all_private(_, msg: Message):
    print(f"[DEBUG] Private message received: {msg.text} from {msg.from_user.id}")
    await msg.reply("👀 I see you! But that’s not a valid command. Try /start or /verify!")

keep_alive()

async def main():
    await app.start()
    me = await app.get_me()
    print(f"✅ Logged in as {me.username} ({me.id})")
    await set_bot_user()
    await app.send_message(OWNER_ID, "👀 Bot is alive, this is a test message.")
    print("🤖 MegaBot is alive and slaying!")
    print("📬 Registered handlers:")
    print(app.handlers["message"])
    await asyncio.Event().wait()  # This keeps it alive like idle() used to

asyncio.run(main())

