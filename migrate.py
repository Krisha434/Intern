import sqlite3
import os
import shutil
import logging
from datetime import datetime

DB_PATH = "task_manager.db"
BACKUP_PATH = "task_manager_backup.db"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

# New schema (defined in this file since queries.py cannot be changed)
CREATE_TASKS_NEW = """
CREATE TABLE IF NOT EXISTS tasks_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK(priority IN ('Low', 'Medium', 'High')) NOT NULL,
    due_date TEXT,
    completed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    tags TEXT
);
"""

INSERT_INTO_TASKS_NEW = """
INSERT INTO tasks_new (
    id, title, description, priority, due_date, completed, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?);
"""

DROP_OLD_TABLE = "DROP TABLE IF EXISTS tasks;"
RENAME_NEW_TABLE = "ALTER TABLE tasks_new RENAME TO tasks;"


def backup_database():
    """Create a backup database before migration"""
    if os.path.exists(DB_PATH):
        try:
            shutil.copy(DB_PATH, BACKUP_PATH)
            logging.info(f"Backup created at '{BACKUP_PATH}'")
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            exit(1)
    else:
        logging.error("Database not found.")
        exit(1)


def create_new_table(cursor):
    """Create the new table with additional columns."""
    try:
        cursor.execute(CREATE_TASKS_NEW)
        logging.info("New table 'tasks_new' created.")
    except Exception as e:
        raise Exception(f"Error creating new table: {e}")


def copy_data(cursor):
    """Copy data from old table into new, adding a timestamp."""
    try:
        cursor.execute("SELECT id, title, description, priority, due_date, completed FROM tasks")
        rows = cursor.fetchall()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            cursor.execute(INSERT_INTO_TASKS_NEW, (*row, now))
        logging.info(f"Copied {len(rows)} records to new table with current timestamp.")
    except Exception as e:
        raise Exception(f"Error copying data: {e}")


def replace_old_table(cursor):
    """Drop old table and rename new one."""
    try:
        cursor.execute(DROP_OLD_TABLE)
        cursor.execute(RENAME_NEW_TABLE)
        logging.info("Replaced old table with new schema.")
    except Exception as e:
        raise Exception(f"Error renaming table: {e}")


def migrate():
    """Run the full migration process."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            create_new_table(cursor)
            copy_data(cursor)
            replace_old_table(cursor)
            conn.commit()
            logging.info("Migration completed successfully.")
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        try:
            conn.rollback()
        except:
            pass


if __name__ == "__main__":
    logging.info("Starting schema migration...")
    backup_database()
    migrate()