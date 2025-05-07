import sqlite3
import random
import string
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Database setup
conn = sqlite3.connect("task_manager.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK(priority IN ('Low', 'Medium', 'High')) NOT NULL,
    due_date TEXT,
    completed INTEGER DEFAULT 0
);
""")
conn.commit()

# Generate random task data
def random_task():
    title = "Task " + ''.join(random.choices(string.ascii_letters, k=6))
    description = "Desc " + ''.join(random.choices(string.ascii_letters + ' ', k=20))
    priority = random.choice(['Low', 'Medium', 'High'])
    due_date = (datetime.now() + timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
    completed = random.choice([0, 1])
    return (title, description, priority, due_date, completed)

# Prepopulate with 100 tasks
cursor.executemany(
    "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
    [random_task() for _ in range(100)]
)
conn.commit()

# Benchmark settings
iterations = 100
insert_times = []
select_times = []
update_times = []
delete_times = []

# Benchmark INSERT
for _ in range(iterations):
    task = random_task()
    start = time.perf_counter()
    cursor.execute(
        "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
        task
    )
    conn.commit()
    end = time.perf_counter()
    insert_times.append(end - start)

# Benchmark SELECT
task_ids = [row[0] for row in cursor.execute("SELECT id FROM tasks").fetchall()]
for _ in range(iterations):
    task_id = random.choice(task_ids)
    start = time.perf_counter()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    cursor.fetchone()
    end = time.perf_counter()
    select_times.append(end - start)

# Benchmark UPDATE
for _ in range(iterations):
    task_id = random.choice(task_ids)
    task = random_task()
    start = time.perf_counter()
    cursor.execute("""
        UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?, completed = ?
        WHERE id = ?
    """, (*task, task_id))
    conn.commit()
    end = time.perf_counter()
    update_times.append(end - start)

# Benchmark DELETE
deleted_ids = []
for _ in range(iterations):
    task_id = random.choice(task_ids)
    deleted_ids.append(task_id)
    start = time.perf_counter()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    end = time.perf_counter()
    delete_times.append(end - start)

# Restore deleted rows
cursor.executemany(
    "INSERT INTO tasks (title, description, priority, due_date, completed) VALUES (?, ?, ?, ?, ?)",
    [random_task() for _ in deleted_ids]
)
conn.commit()

# Compute averages
avg_insert = sum(insert_times) / iterations
avg_select = sum(select_times) / iterations
avg_update = sum(update_times) / iterations
avg_delete = sum(delete_times) / iterations

# Print benchmark timings
print("\n--- SQLite Task DB Benchmark Report ---")
print(f"Executed each query type {iterations} times.\n")
print(f"Average INSERT time: {avg_insert:.6f} seconds")
print(f"Average SELECT time: {avg_select:.6f} seconds")
print(f"Average UPDATE time: {avg_update:.6f} seconds")
print(f"Average DELETE time: {avg_delete:.6f} seconds\n")

# Plotting
operations = ['INSERT', 'SELECT', 'UPDATE', 'DELETE']
times = [avg_insert, avg_select, avg_update, avg_delete]

plt.figure(figsize=(6, 4))
bars = plt.bar(operations, times, color=['skyblue', 'lightgreen', 'salmon', 'violet'])
plt.title('Average Query Execution Time')
plt.ylabel('Time (seconds)')
plt.xlabel('Query Type')
plt.tight_layout()

for bar, time_val in zip(bars, times):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{time_val:.6f}", ha='center', va='bottom')

plt.savefig("visual.png")
plt.close()

# Generate HTML report
html = f"""
<!DOCTYPE html>
<html>
<head><title>SQLite Performance Report</title></head>
<body>
    <h1>SQLite Task DB Query Performance Report</h1>
    <p>Each query was executed {iterations} times. Average execution times are:</p>
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

with open("report.html", "w") as f:
    f.write(html)

print("Report saved as 'report.html'")
print("Performance chart saved as 'visual.png'\n")

# Close DB
conn.close()