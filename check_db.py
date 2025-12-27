import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    vehicle TEXT,
    distance REAL,
    date TEXT
)
""")

conn.commit()
conn.close()

print("Trips table ready")
