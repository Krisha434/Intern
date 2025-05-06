import sqlite3
import os
from dotenv import load_dotenv
from queries import CREATE_TASKS_TABLE

load_dotenv()
DB_PATH = os.getenv("DB_PATH")

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tasks_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute(CREATE_TASKS_TABLE)
    conn.commit()
    conn.close()