import sqlite3
import os

DB_PATH = "resource_hub.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ohrid TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        host_id INTEGER,
        guest_id INTEGER,
        room_id INTEGER,
        datetime TEXT NOT NULL,
        FOREIGN KEY(host_id) REFERENCES users(id),
        FOREIGN KEY(guest_id) REFERENCES users(id),
        FOREIGN KEY(room_id) REFERENCES rooms(id)
    )
    ''')

    # Seed static rooms only — users come from Keycloak via DCR
    cursor.execute('SELECT COUNT(*) FROM rooms')
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO rooms (name, capacity) VALUES (?, ?)", [
            ("Alpha Room", 10),
            ("Beta Room", 5),
            ("Gamma Presentation Hall", 50),
        ])

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

init_db()
