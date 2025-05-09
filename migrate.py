import sqlite3
import os
import shutil
from sqlite3 import Error

DB_PATH = "task_manager.db"
BACKUP_PATH = "task_manager_backup.db"

def backup_database():
    """
    Creates a backup of the existing SQLite database before migration.
    """
    if os.path.exists(DB_PATH):
        try:
            shutil.copy(DB_PATH, BACKUP_PATH)
            print(f"Backup created at '{BACKUP_PATH}'")
        except Exception as e:
            print(f"Failed to create backup: {e}")
            exit(1)
    else:
        print("Database not found. Migration aborted.")
        exit(1)

def create_new_schema(cursor):
    """
    Creates a new tasks table with updated schema, including:
    - created_at (timestamp)
    - tags (optional text)
    """
    try:
        cursor.execute("""
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
        """)
        print("New schema created successfully.")
    except Error as e:
        raise Exception(f"Error creating new table: {e}")

def copy_data_to_new_table(cursor):
    """
    Copies data from the old `tasks` table to the new `tasks_new` table.
    Only includes fields that match the old structure. New columns get defaults.
    """
    try:
        cursor.execute("SELECT * FROM tasks")
        old_data = cursor.fetchall()

        for row in old_data:
            cursor.execute("""
                INSERT INTO tasks_new (id, title, description, priority, due_date, completed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row[:6])  # Only map old columns

        print(f"Copied {len(old_data)} rows into new schema.")
    except Error as e:
        raise Exception(f"Error copying data to new table: {e}")

def replace_old_table(cursor):
    """
    Replaces the old `tasks` table with the newly migrated `tasks_new` table.
    """
    try:
        cursor.execute("DROP TABLE tasks;")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks;")
        print("Old table dropped and new table renamed successfully.")
    except Error as e:
        raise Exception(f"Error replacing old table: {e}")

def migrate_schema():
    """
    Main migration function to handle schema transformation steps.
    Includes creating new schema, copying data, and replacing the old table.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            create_new_schema(cursor)
            copy_data_to_new_table(cursor)
            replace_old_table(cursor)
            conn.commit()
            print("Migration completed successfully.")
    except Exception as migration_error:
        print(f"Migration failed: {migration_error}")
        print("Rolling back changes...")
        conn.rollback()

if __name__ == "__main__":
    print("Starting schema migration...")
    backup_database()
    migrate_schema()
    