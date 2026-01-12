import psycopg2
import os

def init_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
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
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS electricity (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            month TEXT,
            units REAL,
            co2 REAL,
            bill_file TEXT,
            uploaded_at TEXT
        );
    """)

    conn.commit()
    c.close()
    conn.close()
