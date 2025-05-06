from database import get_connection, create_tasks_table
from queries import INSERT_TASK, GET_ALL_TASKS, DELETE_TASK, UPDATE_TASK

def add_task(title, description, priority, due_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute(INSERT_TASK, (title, description, priority, due_date))
    conn.commit()
    conn.close()
    print("Task added successfully.")

def get_all_tasks():
    conn = get_connection()
    c = conn.cursor()
    c.execute(GET_ALL_TASKS)
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task(task_id, title, description, priority, due_date, completed):
    conn = get_connection()
    c = conn.cursor()
    c.execute(UPDATE_TASK, (title, description, priority, due_date, completed, task_id))
    conn.commit()
    conn.close()
    print("Task updated successfully.")

def delete_task(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(DELETE_TASK, (task_id,))
    conn.commit()
    conn.close()
    print("Task deleted successfully.")

def show_menu():
    while True:
        print("\nTask Manager Menu:")
        print("1. Add Task")
        print("2. View All Tasks")
        print("3. Update Task")
        print("4. Delete Task")
        print("5. Exit")

        choice = input("Enter choice: ")

        if choice == '1':
            title = input("Title: ")
            description = input("Description: ")
            priority = input("Priority (Low/Medium/High): ")
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
            priority = input("New Priority (Low/Medium/High): ")
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

if __name__ == "__main__":
    create_tasks_table()
    show_menu()
tasks = get_all_tasks()
for task in tasks:
    print(task)