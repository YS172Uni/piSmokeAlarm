import sqlite3

DB_PATH = "events.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create the events table
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
print("Database initialized with table 'events'.")
