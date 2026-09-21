import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]
EXAMPLE_TASKS = (
    ("Learn FastAPI", False),
    ("Connect SQLite", False),
    ("Build a CRUD API", False),
)


def initialize_database():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )"""
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM tasks")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)", EXAMPLE_TASKS
                )


def list_tasks():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        return connection.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def get_task(task_id):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        return connection.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()


def create_task(title):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        return connection.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, FALSE) RETURNING *",
            (title,),
        ).fetchone()


def update_task(task_id, title, done):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        return connection.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def delete_task(task_id):
    with psycopg.connect(DATABASE_URL) as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cursor.rowcount > 0
