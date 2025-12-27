import sqlite3

db = sqlite3.connect("database.db")
c = db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS electricity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT NOT NULL,
    month TEXT NOT NULL,
    units REAL NOT NULL,
    co2 REAL NOT NULL,
    bill_file TEXT,
    uploaded_at TEXT
)
""")

db.commit()
db.close()

print("✅ Electricity table created successfully")
