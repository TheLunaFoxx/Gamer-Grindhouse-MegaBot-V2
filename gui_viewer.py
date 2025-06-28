# gui_viewer.py

from flask import Flask, render_template_string
from datetime import datetime, timezone
import os
import threading

# We'll import the `frees` object from the main bot script
# But for this separate version, we simulate the frees dict:
frees = {
    -1001234567890: {
        123456789: datetime.now(timezone.utc) + timedelta(days=1),
        987654321: None,
    },
    -1002223334445: {
        123456789: datetime.now(timezone.utc) + timedelta(hours=6),
    },
}

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Frees Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; background: #111; color: #eee; padding: 20px; }
        h1 { color: #ff79c6; }
        .group { margin-bottom: 30px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; }
        th, td { border: 1px solid #444; padding: 8px; text-align: left; }
        th { background: #222; }
        tr:nth-child(even) { background: #1a1a1a; }
    </style>
</head>
<body>
    <h1>👀 Current Frees Viewer</h1>
    {% for chat_id, users in frees.items() %}
        <div class="group">
            <h2>Group: {{ chat_id }}</h2>
            <table>
                <tr><th>User ID</th><th>Status</th><th>Until</th></tr>
                {% for user_id, until in users.items() %}
                <tr>
                    <td>{{ user_id }}</td>
                    <td>{{ 'Forever' if until is none else 'Temporary' }}</td>
                    <td>{{ '—' if until is none else until.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    {% endfor %}
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(TEMPLATE, frees=frees)

def run_gui():
    app.run(host="0.0.0.0", port=6969)

if __name__ == "__main__":
    run_gui()

# Later in main.py, you can import this file and run it in a thread:
# from gui_viewer import run_gui
# threading.Thread(target=run_gui).start()
