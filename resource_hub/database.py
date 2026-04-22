import sqlite3
import os

DB_PATH = "resource_hub.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Open',
        creator_id INTEGER,
        FOREIGN KEY(creator_id) REFERENCES users(id)
    )
    ''')

    # Seed data
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (name, email) VALUES ('Admin Manager', 'admin@cenrixa.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Trainee One', 'trainee1@cenrixa.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Trainee Two', 'trainee2@cenrixa.com')")

        cursor.execute("INSERT INTO rooms (name, capacity) VALUES ('Alpha Room', 10)")
        cursor.execute("INSERT INTO rooms (name, capacity) VALUES ('Beta Room', 5)")
        cursor.execute("INSERT INTO rooms (name, capacity) VALUES ('Gamma Presentation Hall', 50)")

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize DB on import
init_db()
