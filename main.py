from database import get_connection, create_tasks_table
from queries import INSERT_TASK, GET_ALL_TASKS, DELETE_TASK, UPDATE_TASK

VALID_PRIORITIES = {"Low", "Medium", "High"}

def validate_priority(priority):
    if priority not in VALID_PRIORITIES:
        raise ValueError("Priority must be one of: Low, Medium, High")

def add_task(title, description, priority, due_date):
    try:
        validate_priority(priority)
        with get_connection() as conn:
            conn.execute(INSERT_TASK, (title, description, priority, due_date))
        print("Task added successfully.")
    except (ValueError, Exception) as e:
        print(f"Error adding task: {e}")

def get_all_tasks():
    try:
        with get_connection() as conn:
            return conn.execute(GET_ALL_TASKS).fetchall()
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def update_task(task_id, title, description, priority, due_date, completed):
    try:
        validate_priority(priority)
        with get_connection() as conn:
            conn.execute(UPDATE_TASK, (title, description, priority, due_date, completed, task_id))
        print("Task updated successfully.")
    except (ValueError, Exception) as e:
        print(f"Error updating task: {e}")

def delete_task(task_id):
    try:
        with get_connection() as conn:
            conn.execute(DELETE_TASK, (task_id,))
        print("Task deleted successfully.")
    except Exception as e:
        print(f"Error deleting task: {e}")

def show_menu():
    while True:
        print("\nTask Manager Menu:")
        print("1. Add Task")
        print("2. View All Tasks")
        print("3. Update Task")
        print("4. Delete Task")
        print("5. Exit")

        choice = input("Enter choice: ")

        try:
            if choice == '1':
                title = input("Title: ")
                description = input("Description: ")
                priority = input("Priority (Low/Medium/High): ").capitalize()
                due_date = input("Due Date (YYYY-MM-DD): ")
                add_task(title, description, priority, due_date)

            elif choice == '2':
                tasks = get_all_tasks()
                for task in tasks:
                    print(task)

            elif choice == '3':
                task_id = int(input("Task ID to update: "))
                title = input("New Title: ")
                description = input("New Description: ")
                priority = input("New Priority (Low/Medium/High): ").capitalize()
                due_date = input("New Due Date (YYYY-MM-DD): ")
                completed = int(input("Completed (0 for No, 1 for Yes): "))
                update_task(task_id, title, description, priority, due_date, completed)

            elif choice == '4':
                task_id = int(input("Task ID to delete: "))
                delete_task(task_id)

            elif choice == '5':
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Try again.")

        except ValueError as e:
            print(f"Invalid input: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    create_tasks_table()
    show_menu()
tasks = get_all_tasks()
for task in tasks:
    print(task)