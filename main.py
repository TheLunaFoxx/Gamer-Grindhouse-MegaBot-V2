import asyncio
import os
import re
import threading
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from flask import Flask, render_template_string, request, redirect, url_for, send_file, jsonify
from shared import frees
import io 

# --- GUI Setup ---
# Create Flask app
flask_app = Flask(__name__)

load_dotenv()
print("API_ID from env:", os.getenv("API_ID"))
os.makedirs("/data", exist_ok=True)  # ensure volume directory exists

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7868250691
LOG_FILE = "verified_users.txt"

# --- Bot State + Cache ---
user_info_cache = {}  # {user_id: {"first": ..., "last": ..., "username": ...}}
verifying = {}
approved_users = set()
verification_map = {}
FREES_LOG_FILE = "/data/frees_log.txt"
group_names = {}
BOT_USER = None

# --- GUI Information ---
group_icons = {
    -1001234567890: "🎮",
    -1009876543210: "💋",
}

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ Missing API_ID, API_HASH, or BOT_TOKEN environment variables.")

print("🔧 [DEBUG] ENV Loaded:")
print("API_ID:", API_ID)
print("API_HASH:", API_HASH)
print("BOT_TOKEN:", "HIDDEN" if BOT_TOKEN else "None")

app = Client(
    "megabot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN"),
)


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
        "d": timedelta(days=value),
        "h": timedelta(hours=value),
        "m": timedelta(minutes=value),
    }.get(unit, None)


@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    print(f"[DEBUG] /start command received from: {msg.from_user.id}")
    try:
        await msg.reply_text(
            f"Welcome to <b>Gamer Grindhouse Network Verification Bot {msg.from_user.mention}!</b> 🎮\n\nClick /verify to continue ❤️",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"[ERROR] Failed to send /start message: {e}")


@app.on_message(filters.command("verify") & filters.private)
async def verify(_, msg: Message):
    username = msg.from_user.username or msg.from_user.first_name
    verifying[msg.from_user.id] = {"video": None, "photo": None}
    await msg.reply_text(
        f"It's time to verify {username}!\n\n🎥 Please click the mic in the bottom right corner to change it to a camera. Then, <b>long-press the camera</b> to record a live video saying <b>today's date, your username, and 'verifying for Gamer Grindhouse'.</b>\n📸 Then send a <b>screenshot of your ID</b> or <b>18+ website profile <i>(Onlyfans, Fansly etc. Make sure your username is visible!)</i></b>.\n\nPlease send them <b>in this order</b> to ensure your information is sent to the owner correctly! ❤️",
        parse_mode=ParseMode.HTML,
    )


@app.on_message(filters.private & filters.video_note)
async def video_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]["video"] = msg
        await msg.reply(
            "✅ Video received! Now please send your <b>ID</b> or <b>website screenshot!</b>",
            parse_mode=ParseMode.HTML,
        )


@app.on_message(filters.private & filters.photo)
async def photo_received(_, msg: Message):
    if msg.from_user.id in verifying:
        verifying[msg.from_user.id]["photo"] = msg
        data = verifying[msg.from_user.id]
        await msg.reply(
            "🎉 Your verification has been sent to the owner, and a decision will be made <b><i>ASAP!</i></b>",
            parse_mode=ParseMode.HTML,
        )

        video_msg = data["video"]
        photo_msg = data["photo"]

        fwd_video = await app.forward_messages(OWNER_ID, msg.chat.id, video_msg.id)
        fwd_photo = await app.forward_messages(OWNER_ID, msg.chat.id, photo_msg.id)

        verification_map[fwd_video.id] = msg.from_user.id
        verification_map[fwd_photo.id] = msg.from_user.id

        await app.send_message(
            OWNER_ID,
            f"⚠️ Don’t forget to check @{msg.from_user.username or msg.from_user.first_name}'s fedbans!",
        )


@app.on_message(filters.private & filters.reply & filters.user(OWNER_ID))
async def approve_or_reject(_, msg: Message):
    replied_msg = msg.reply_to_message
    user_id = verification_map.get(replied_msg.id)

    if not user_id:
        return await msg.reply(
            "❌ <b>Couldn’t match this verification to a user.</b>\nPlease ask them to <b>restart</b>.",
            parse_mode=ParseMode.HTML,
        )

    if msg.text.lower().startswith("approve"):
        user_info = await app.get_users(user_id)
        if user_info.username != "TestLunaFoxx":
            approved_users.add(user_id)
            with open(LOG_FILE, "a") as f:
                f.write(f"{user_id}\n")
        await app.send_message(
            user_id,
            "✅ <b>You're approved!</b> Welcome to the network!\nClick below to join the network and groups 👇\n<b><u>https://t.me/addlist/mt_KC0gfZBkzMzk0</u></b>\n\nRules:\n✅ Please ensure you <b>complete your POP to unlock</b> within <b>24 hours</b> of joining the network,\n✅ <b><u>SFW flyers only</u></b>. This means <b>no <i>nips</i>, <i>bits</i> or <i>cracks</i></b> to be visible AT ALL (they can be <b>blurred</b>, don't worry!),\n✅ Do <b><u>NOT</u></b> message potential buyers first. If you are caught doing this, it will result in an <b>instant ban and fedban against your name</b>,\n✅ <b>Assistants</b> are allowed to complete POP on your behalf, but please direct them to myself (<u>@GamerGrindhouseMegaBot</u>) to <b>complete verification</b>!",
            parse_mode=ParseMode.HTML,
        )

    elif msg.text.lower().startswith("reject"):
        reason = msg.text.split(" ", 1)[1] if " " in msg.text else "No reason provided"
        await app.send_message(
            user_id,
            f"❌ <b>Verification rejected:</b> {reason}\n<b>Try again</b> with /verify or contact @The_LunaFoxx if you're having any issues!",
            parse_mode=ParseMode.HTML,
        )


@app.on_message(filters.command("free") & filters.group)
async def free(_, msg: Message):
    chat_id = msg.chat.id
    chat_member = await app.get_chat_member(chat_id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ):
        return

    try:
        target = await app.get_users(msg.command[1])
        chat_member = await app.get_chat_member(chat_id, target.id)

        user_info_cache[target.id] = {
            "first": target.first_name or "",
            "last": target.last_name or "",
            "username": target.username or None,
            "is_admin": chat_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER),
            "is_bot": target.is_bot,
        }
    except:
        await msg.reply("❌ <b>Couldn't find that user.</b>", parse_mode=ParseMode.HTML)
        return

    tdelta = parse_time(msg.command[2])
    if tdelta is None and msg.command[2] != "0":
        await msg.reply("Invalid format. Use 1d, 2h, 30m or 0 for forever.")
        return

    until = None if msg.command[2] == "0" else datetime.now(timezone.utc) + tdelta
    group_frees = frees.setdefault(chat_id, {})
    group_frees[target.id] = until

    await msg.reply(
        f"✅ <b>{target.mention} has been free'd</b> {'forever' if until is None else f'until {until}'}",
        parse_mode=ParseMode.HTML,
    )


@app.on_message(filters.command("unfree") & filters.group)
async def unfree(_, msg: Message):
    chat_id = msg.chat.id
    chat_member = await app.get_chat_member(chat_id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ):
        return

    try:
        target = await app.get_users(msg.command[1])
    except:
        await msg.reply("❌ <b>Couldn't find that user.</b>", parse_mode=ParseMode.HTML)
        return

    group_frees = frees.get(chat_id, {})
    if target.id in group_frees:
        del group_frees[target.id]
        await msg.reply(
            f"❌ <b>{target.mention} has been unfree'd.</b>", parse_mode=ParseMode.HTML
        )


@app.on_message(filters.command("unfree_all") & filters.group)
async def unfree_all(_, msg: Message):
    chat_id = msg.chat.id
    chat_member = await app.get_chat_member(chat_id, msg.from_user.id)
    if msg.from_user.id != OWNER_ID and chat_member.status not in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ):
        return

    frees[chat_id] = {}
    await msg.reply("🧹 <b>All users have been unfree'd.</b>", parse_mode=ParseMode.HTML)


@app.on_message(filters.group)
async def auto_delete(_, msg: Message):
    chat_id = msg.chat.id
    user_id = msg.from_user.id

    # ✅ Store group name for GUI
    if chat_id not in group_names:
        group_names[chat_id] = msg.chat.title or f"Group {chat_id}"

    # ✅ Cache user info if not already stored
    if user_id not in user_info_cache:
        chat_member = await app.get_chat_member(chat_id, user_id)
        user_info_cache[user_id] = {
            "first": msg.from_user.first_name or "",
            "last": msg.from_user.last_name or "",
            "username": msg.from_user.username or None,
            "is_admin": chat_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER),
            "is_bot": msg.from_user.is_bot,
        }

    # Skip bots and owner
    if user_id == OWNER_ID or msg.from_user.is_bot:
        return

    group_frees = frees.get(chat_id, {})

    if user_id in group_frees:
        until = group_frees[user_id]
        if until and datetime.now(timezone.utc) > until:
            del group_frees[user_id]
        else:
            return  # User is free, do nothing

    # User is not free — delete message
    try:
        await msg.delete()
        print(f"[DEBUG] Deleted message from {user_id} in {chat_id}")
    except Exception as e:
        print(f"[ERROR] Couldn't delete message from {user_id} in {chat_id}: {e}")


@app.on_chat_member_updated()
async def on_chat_member_update(_, event):
    if not event.new_chat_member or not event.old_chat_member:
        print("[WARN] Chat member update missing data — skipping.")
        return

    if not event.new_chat_member.user:
        print("[WARN] new_chat_member has no user info.")
        return

    user = event.new_chat_member.user
    chat_id = event.chat.id

    if user.id not in user_info_cache:
        try:
            member = await app.get_chat_member(chat_id, user.id)
            user_info_cache[user.id] = {
                "first": user.first_name or "",
                "last": user.last_name or "",
                "username": user.username or None,
                "is_admin": member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER),
                "is_bot": user.is_bot,
            }
        except Exception as e:
            print(f"[ERROR] Failed to cache member info for {user.id}: {e}")

    # Only act on NEW joiners
    if (
        event.old_chat_member.status not in ("member", "restricted")
        and event.new_chat_member.status == "member"
    ):

        # Skip owner, admins, bots
        try:
            member = await app.get_chat_member(chat_id, user.id)
        except Exception as e:
            print(f"[ERROR] Failed to get member info: {e}")
            return

        if (
            member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
            or user.is_bot
            or user.id == OWNER_ID
        ):
            return

        # Remove from frees
        if user.id in frees.get(chat_id, {}):
            del frees[chat_id][user.id]

        await app.send_message(
            chat_id,
            f"❌ <b>{user.mention} has been unfree'd.</b> They must complete POP to post if they are a model!",
            parse_mode=ParseMode.HTML,
        )
        print(f"[DEBUG] {user.id} removed from frees[{chat_id}] on join")


@app.on_message(filters.private)
async def all_private(client, msg: Message):
    try:
        print(f"[PRIVATE DEBUG] Message from {msg.from_user.id}: {msg.text}")
        await msg.reply("⚡ I received your message!")
    except Exception as e:
        print(f"[ERROR] while handling private message: {e}")


@app.on_message(
    filters.command("view_frees") & filters.private & filters.user(OWNER_ID)
)
async def view_frees_log(_, msg: Message):
    try:
        with open("/data/frees_log.txt", "r") as f:
            content = f.read()
            if not content:
                await msg.reply("📂 Log is empty, baby!")
            else:
                await msg.reply(
                    f"📄 <b>frees_log.txt:</b>\n<code>{content}</code>",
                    parse_mode=ParseMode.HTML,
                )
    except Exception as e:
        await msg.reply(f"❌ Couldn't read the log: {e}")


gui_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Frees Viewer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #121212;
            color: #f2f2f2;
            padding: 2em;
        }

        h1 {
            color: #ff5fcf;
            font-size: 2.5em;
            border-bottom: 2px solid #ff5fcf;
            padding-bottom: 0.2em;
            margin-bottom: 1em;
        }

        .filter-bar {
            margin-bottom: 2em;
        }

        .filter-bar input {
            padding: 0.4em;
            font-size: 1em;
            width: 250px;
            border-radius: 6px;
            border: 1px solid #555;
            background: #1e1e1e;
            color: #fff;
        }

        .group {
            margin-bottom: 2em;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 1em;
            background: #1e1e1e;
        }

        .group h2 {
            color: #76e0ff;
            margin-bottom: 0.5em;
        }

        .group .meta {
            font-size: 0.9em;
            color: #ccc;
            margin-bottom: 1em;
        }

        .user {
            margin-left: 1em;
            margin-bottom: 0.6em;
            font-size: 1em;
            padding: 0.7em;
            border-left: 4px solid #ff5fcf;
            background-color: #1a1a1a;
            border-radius: 5px;
        }

        .forever { border-left-color: #7fff7f; background-color: #193219; }
        .admin   { border-left-color: #7fafff; background-color: #182c3a; }
        .bot     { border-left-color: #c67fff; background-color: #2b1c37; }

        .btn {
            background: #ff5fcf;
            color: #fff;
            padding: 0.4em 1em;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }

        .btn:hover {
            background: #ff85da;
        }

        .footer {
            margin-top: 3em;
            font-size: 0.9em;
            color: #888;
            text-align: center;
        }

        code {
            color: #00ffc3;
        }
    </style>
    <script>
        function filterFrees() {
            const input = document.getElementById("filterInput").value.toLowerCase();
            const groups = document.getElementsByClassName("group");

            for (const group of groups) {
                const users = group.getElementsByClassName("user");
                let groupMatch = false;

                for (const user of users) {
                    const text = user.innerText.toLowerCase();
                    const match = text.includes(input);
                    user.style.display = match ? "block" : "none";
                    if (match) groupMatch = true;
                }

                group.style.display = groupMatch ? "block" : "none";
            }
        }

        function confirmUnfree(chat_id) {
            if (confirm("Are you sure you want to unfree EVERYONE in this group?!")) {
                fetch(`/unfree_all/${chat_id}`).then(() => location.reload());
            }
        }

        function exportList() {
            window.location.href = "/export";
        }
    </script>
</head>
<body>
    <h1>👀 Frees Viewer</h1>

    <div class="filter-bar">
        🔍 <input type="text" id="filterInput" onkeyup="filterFrees()" placeholder="Filter by group or user...">
        <button class="btn" onclick="exportList()">📤 Export List</button>
    </div>

    {% if frees %}
        {% for chat_id, users in frees.items() %}
            <div class="group">
                <h2>
                    {% if group_icons.get(chat_id) %}
                        {{ group_icons[chat_id] }}
                    {% endif %}
                    {{ group_names.get(chat_id, 'Group ' ~ chat_id) }}
                </h2>
                <div class="meta">
                    👥 {{ users|length }} freed | 🆔 <code>{{ chat_id }}</code>
                    <button class="btn" onclick="confirmUnfree({{ chat_id }})" style="float:right">❌ Unfree All</button>
                </div>
                {% for user_id, until in users.items() %}
                    {% set info = user_info_cache.get(user_id, {}) %}
                    {% set tag = "forever" if not until else "" %}
                    {% set tag = tag if tag else ("admin" if info.get("is_admin") else "bot" if info.get("is_bot") else "") %}
                    <div class="user {{ tag }}">
                        🔓 <b>User ID:</b> {{ user_id }}<br>
                        <b>Name:</b> {{ info.get("first", "Unknown") }} {{ info.get("last", "") }}<br>
                        <b>Username:</b> {{ "@" ~ info["username"] if info.get("username") else "No username" }}<br>
                        <b>Free:</b> 
                            {% if until %}
                                until {{ until }} ({{ ((until - now).total_seconds() // 60)|int }} mins left)
                            {% else %}
                                forever
                            {% endif %}
                    </div>
                {% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No users currently free in any group. 💤</p>
    {% endif %}

    <div class="footer">
        🔐 This viewer is live and private. You are slaying responsibly.
    </div>
</body>
</html>
"""

@flask_app.route("/")
def view_frees():
    return render_template_string(
        gui_template,
        frees=frees,
        group_names=group_names,
        group_icons=group_icons,
        user_info_cache=user_info_cache,
        now=datetime.now(timezone.utc),
    )

@flask_app.route("/export")
def export():
    try:
        with open(FREES_LOG_FILE, "r") as f:
            return send_file(
                io.BytesIO(f.read().encode()),
                mimetype="text/plain",
                as_attachment=True,
                download_name="frees_log.txt"
            )
    except Exception as e:
        return f"Error: {e}", 500

def run_gui():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


def keep_alive():
    threading.Thread(target=run_gui).start()


keep_alive()
app.run()
