# merged_gui_keepalive.py

from flask import Flask
import threading
from datetime import datetime, timezone
import os

# Update this with your frees dict if needed
from main import frees  # circular import is okay in this context

app = Flask(__name__)

@app.route("/gui")
def gui():
    html = "<h1>👀 Frees Viewer</h1><ul>"
    for chat_id, users in frees.items():
        html += f"<li><b>Group {chat_id}</b><ul>"
        for user_id, until in users.items():
            if until:
                time_str = until.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "Forever"
            html += f"<li>User {user_id}: {time_str}</li>"
        html += "</ul></li>"
    html += "</ul>"
    return html

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    thread = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port})
    thread.start()
