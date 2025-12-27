import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

c.execute("""
CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTimport sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

# USERS TABLE
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# TRIPS TABLE (MATCHES YOUR app.py EXACTLY)
c.execute("""
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    mode TEXT,
    vehicle TEXT,
    distance REAL,
    date TEXT,

    start_lat REAL,
    start_lon REAL,
    end_lat REAL,
    end_lon REAL,
    start_time TEXT,
    end_time TEXT
)
""")

conn.commit()
conn.close()

print("✅ Database initialized successfully")
OINCREMENT,
    user TEXT,
    mode TEXT,
    vehicle TEXT,
    distance REAL,
    date TEXT,

    start_lat REAL,
    start_lon REAL,
    end_lat REAL,
    end_lon REAL,
    start_time TEXT,
    end_time TEXT
)
""")

conn.commit()
conn.close()
print("Database initialized")
