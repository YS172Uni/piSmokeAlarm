import sqlite3

class Database:
    def __init__(self, db_path="events.db"):
        self.db_path = db_path

    def initialise(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detected INTEGER,
            timestamp TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()
        print(f"Database '{self.db_path}' initialised with table 'events'.")
