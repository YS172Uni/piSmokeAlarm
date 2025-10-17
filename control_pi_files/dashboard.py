from flask import Flask, render_template
import sqlite3
from datetime import datetime
import logging

class Dashboard:
    def __init__(self, db_path="events.db"):
        self.app = Flask(__name__)
        self.DB_PATH = db_path
        self._setup_routes()
        log = logging.getLogger('werkzeug')
        log.handlers = []                   
        log.addHandler(logging.NullHandler())  
        log.propagate = False               
        log.setLevel(logging.CRITICAL) 

    def get_events(self, limit=50):
        """Fetch latest events from SQLite."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT node, event_type, detected, timestamp FROM events ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            events = self.get_events()
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
        #refresh the page every 5 seconds
        @self.app.route("/events_json")
        def events_json():
            events = self.get_events()
            formatted_events = [
                {
                    "node": row[0],
                    "event_type": row[1],
                    "detected": row[2] if row[2] is not None else "-",
                    "timestamp": datetime.fromisoformat(row[3]).strftime("%Y-%m-%d %H:%M:%S")
                }
                for row in events
            ]
            from flask import jsonify
            return jsonify(formatted_events)

    def run(self, host="0.0.0.0", port=5000, debug=False):
        self.app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
