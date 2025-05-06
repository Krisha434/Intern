import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    db_path = os.getenv("DB_PATH")
    if not db_path:
        raise ValueError("Database path not found in environment variables (.env)")
    return sqlite3.connect(db_path)

def create_tasks_table():
    from queries import CREATE_TASKS_TABLE
    try:
        with get_connection() as conn:
            conn.execute(CREATE_TASKS_TABLE)
    except sqlite3.Error as e:
        print(f"Error creating tasks table: {e}")