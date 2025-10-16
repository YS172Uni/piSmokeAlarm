from flask import Flask, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_PATH = "events.db"

def get_events(limit=50):
    """Fetch latest events from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT node, event_type, detected, timestamp FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route("/")
def index():
    events = get_events()
    # Format timestamp nicely
    formatted_events = [
        {
            "node": row[0],
            "event_type": row[1],
            "detected": row[2] if row[2] is not None else "-",
            "timestamp": datetime.fromisoformat(row[3]).strftime("%Y-%m-%d %H:%M:%S")
        }
        for row in events
    ]
    return render_template("index.html", events=formatted_events)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
