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

INSERT_TASK = """
INSERT INTO tasks (title, description, priority, due_date)
VALUES (?, ?, ?, ?);
"""

GET_ALL_TASKS = "SELECT * FROM tasks;"
UPDATE_TASK = "UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?, completed = ? WHERE id = ?;"
DELETE_TASK = "DELETE FROM tasks WHERE id = ?;"