import pytest
import sqlite3
import os
from dotenv import load_dotenv
from database import get_connection, create_tasks_table
from queries import CREATE_TASKS_TABLE, INSERT_TASK, GET_ALL_TASKS, UPDATE_TASK, DELETE_TASK
from main import add_task, get_all_tasks, update_task, delete_task, validate_priority

# Load environment variables for testing
load_dotenv()
TEST_DB_PATH = os.getenv("DB_PATH", "task_manager.db")

@pytest.fixture
def test_db():
    """Sets up an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute(CREATE_TASKS_TABLE)
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture
def app_with_test_db(monkeypatch):
    """Mocks the database connection to use the in-memory test database."""
    def mock_get_connection():
        return sqlite3.connect(":memory:")
    monkeypatch.setattr("database.get_connection", mock_get_connection)
    create_tasks_table() # Ensure the table is created in the test database

def test_get_connection_valid_path(monkeypatch):
    """Tests that get_connection returns a connection object with a valid path."""
    monkeypatch.setenv("DB_PATH", "task_manager.db")
    conn = get_connection()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()

def test_get_connection_missing_path(monkeypatch):
    """Tests that get_connection raises ValueError if DB_PATH is not set."""
    monkeypatch.delenv("DB_PATH", raising=False)
    with pytest.raises(ValueError) as excinfo:
        get_connection()
    assert "Database path not found in environment variables (.env)" in str(excinfo.value)

def test_create_tasks_table(test_db):
    """Tests that create_tasks_table successfully creates the tasks table."""
    cursor = test_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
    table = cursor.fetchone()
    assert table is not None
    assert table[0] == 'tasks'

# --- Tests for queries.py ---

def test_query_definitions():
    """Ensures that the query constants are defined as strings."""
    assert isinstance(CREATE_TASKS_TABLE, str)
    assert isinstance(INSERT_TASK, str)
    assert isinstance(GET_ALL_TASKS, str)
    assert isinstance(UPDATE_TASK, str)
    assert isinstance(DELETE_TASK, str)
    assert "tasks" in CREATE_TASKS_TABLE
    assert "tasks" in INSERT_TASK
    assert "tasks" in GET_ALL_TASKS
    assert "tasks" in UPDATE_TASK
    assert "tasks" in DELETE_TASK

def test_validate_priority_valid():
    """Tests that validate_priority does not raise an error for valid priorities."""
    validate_priority("Low")
    validate_priority("Medium")
    validate_priority("High")

def test_validate_priority_invalid():
    """Tests that validate_priority raises ValueError for invalid priorities."""
    with pytest.raises(ValueError) as excinfo:
        validate_priority("Urgent")
    assert "Priority must be one of: Low, Medium, High" in str(excinfo.value)

def test_add_task(app_with_test_db):
    """Tests that add_task successfully inserts a task into the database."""
    add_task("Buy groceries", "Milk, eggs, bread", "Medium", "2025-05-10")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, priority, due_date FROM tasks WHERE title = ?", ("Buy groceries",))
        task = cursor.fetchone()
        assert task is not None
        assert task == ("Buy groceries", "Milk, eggs, bread", "Medium", "2025-05-10")

def test_update_task(app_with_test_db):
    """Tests that update_task successfully modifies an existing task."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(INSERT_TASK, ("Old Title", "Old Desc", "Low", "2025-05-01"))
        task_id = cursor.lastrowid
        conn.commit()

    update_task(task_id, "New Title", "New Desc", "High", "2025-05-10", 1)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, priority, due_date, completed FROM tasks WHERE id = ?", (task_id,))
        updated_task = cursor.fetchone()
        assert updated_task == ("New Title", "New Desc", "High", "2025-05-10", 1)

def test_delete_task(app_with_test_db):
    """Tests that delete_task successfully removes a task from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(INSERT_TASK, ("Task to Delete", "...", "Medium", "2025-05-25"))
        task_id = cursor.lastrowid
        conn.commit()

    delete_task(task_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        deleted_task = cursor.fetchone()
        assert deleted_task is None