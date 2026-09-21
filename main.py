import os
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse


DATABASE_PATH = Path(os.environ.get("TASKS_DB_PATH", Path(__file__).with_name("tasks.db")))
EXAMPLE_TASKS = (
    ("Learn FastAPI", 0),
    ("Connect SQLite", 0),
    ("Build a CRUD API", 0),
)


def initialize_database():
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0
                )"""
            )
            if connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
                connection.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)", EXAMPLE_TASKS
                )


initialize_database()


app = FastAPI()


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def serialize_task(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.get("/")
def read_root():
    return {"status": "success", "message": "API is live."}


@app.get("/health")
def health_check():
    return {"status": "healthy", "system": "operational"}


@app.get("/tasks")
def list_tasks():
    with closing(get_connection()) as connection:
        return [serialize_task(row) for row in connection.execute("SELECT * FROM tasks")]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with closing(get_connection()) as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return serialize_task(row)
