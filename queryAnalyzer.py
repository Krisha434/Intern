import sqlite3
import random
import string
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

# Constants
DB_PATH = "task_manager.db"
OUTPUT_DIR = "output"
PRIORITY_LEVELS = ['Low', 'Medium', 'High']

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_table():
    """Create the tasks table if it doesn't already exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT CHECK(priority IN ('Low', 'Medium', 'High')) NOT NULL,
                    due_date TEXT,
                    completed INTEGER DEFAULT 0
                );
            """)
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")

def random_task():
    """Generate a random task."""
    title = "Task " + ''.join(random.choices(string.ascii_letters, k=6))
    description = "Desc " + ''.join(random.choices(string.ascii_letters + ' ', k=20))
    priority = random.choice(PRIORITY_LEVELS)
    due_date = (datetime.now() + timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
    completed = random.choice([0, 1])
    return (title, description, priority, due_date, completed)

def batch_insert_tasks(count):
    """Insert a batch of tasks."""
    tasks = [random_task() for _ in range(count)]
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany(
                "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
                tasks
            )
    except sqlite3.Error as e:
        print(f"Error inserting tasks: {e}")

def restore_tasks(count):
    """Restore tasks that were deleted during benchmarking."""
    tasks = [random_task() for _ in range(count)]
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany(
                "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
                tasks
            )
    except sqlite3.Error as e:
        print(f"Error restoring tasks: {e}")

def run_benchmarks(iterations=100):
    """Benchmark the CRUD operations."""
    insert_times = []
    select_times = []
    update_times = []
    delete_times = []

    # INSERT
    for _ in range(iterations):
        task = random_task()
        start = time.perf_counter()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
                task
            )
        insert_times.append(time.perf_counter() - start)

    avg_insert = sum(insert_times) / iterations
    print(f"Average INSERT time: {avg_insert:.6f} seconds")

    # SELECT
    with sqlite3.connect(DB_PATH) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM tasks LIMIT 500").fetchall()]

    for _ in range(iterations):
        task_id = random.choice(task_ids)
        start = time.perf_counter()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        select_times.append(time.perf_counter() - start)

    avg_select = sum(select_times) / iterations
    print(f"Average SELECT time: {avg_select:.6f} seconds")

    # UPDATE
    for _ in range(iterations):
        task_id = random.choice(task_ids)
        task = random_task()
        start = time.perf_counter()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?, completed = ?
                WHERE id = ?
            """, (*task, task_id))
        update_times.append(time.perf_counter() - start)

    avg_update = sum(update_times) / iterations
    print(f"Average UPDATE time: {avg_update:.6f} seconds")

    # DELETE
    deleted_ids = []
    for _ in range(iterations):
        task_id = random.choice(task_ids)
        deleted_ids.append(task_id)
        start = time.perf_counter()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        delete_times.append(time.perf_counter() - start)

    avg_delete = sum(delete_times) / iterations
    print(f"Average DELETE time: {avg_delete:.6f} seconds")

    # Restore deleted tasks
    restore_tasks(len(deleted_ids))

    return avg_insert, avg_select, avg_update, avg_delete

def generate_report(avg_insert, avg_select, avg_update, avg_delete):
    """Generate a bar chart and HTML report of benchmark results."""
    operations = ['INSERT', 'SELECT', 'UPDATE', 'DELETE']
    times = [avg_insert, avg_select, avg_update, avg_delete]

    # Chart
    plt.figure(figsize=(6, 4))
    bars = plt.bar(operations, times, color=['skyblue', 'lightgreen', 'salmon', 'violet'])
    plt.title('Average Query Execution Time')
    plt.ylabel('Time (seconds)')
    plt.xlabel('Query Type')
    plt.tight_layout()

    for bar, time_val in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{time_val:.6f}", ha='center', va='bottom')

    chart_path = os.path.join(OUTPUT_DIR, "visual.png")
    plt.savefig(chart_path)
    plt.close()

    # HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>SQLite Performance Report</title></head>
    <body>
        <h1>SQLite Task DB Query Performance Report</h1>
        <p>Each query was executed 100 times. Average execution times are:</p>
        <ul>
            <li><b>INSERT:</b> {avg_insert:.6f} seconds</li>
            <li><b>SELECT:</b> {avg_select:.6f} seconds</li>
            <li><b>UPDATE:</b> {avg_update:.6f} seconds</li>
            <li><b>DELETE:</b> {avg_delete:.6f} seconds</li>
        </ul>
        <h2>Performance Graph</h2>
        <img src="visual.png" alt="Query Performance Chart">
    </body>
    </html>
    """
    report_path = os.path.join(OUTPUT_DIR, "report.html")
    with open(report_path, "w") as f:
        f.write(html)

# Main entry point
if __name__ == "__main__":
    create_table()
    batch_insert_tasks(100)
    avg_ins, avg_sel, avg_upd, avg_del = run_benchmarks()
    generate_report(avg_ins, avg_sel, avg_upd, avg_del)

    print("\nChart saved to: output/visual.png")
    print("Report saved to: output/report.html")