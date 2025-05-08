CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK(priority IN ('Low', 'Medium', 'High')) NOT NULL,
    due_date TEXT,
    completed INTEGER DEFAULT 0
);
"""

INSERT_TASK = "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)"
SELECT_TASK_ID = "SELECT id FROM tasks LIMIT 1 OFFSET ?"
SELECT_ALL_IDS = "SELECT id FROM tasks"
SELECT_BY_ID = "SELECT * FROM tasks WHERE id = ?"
UPDATE_TASK = """
UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?, completed = ?
WHERE id = ?
"""
DELETE_BY_ID = "DELETE FROM tasks WHERE id = ?"