import os
import sqlite3
from contextlib import closing
from pathlib import Path

import database
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


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


database.initialize_database()
initialize_database()


app = FastAPI()


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def serialize_task(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


async def read_json(request):
    try:
        body = await request.json()
    except Exception:
        return None
    return body if isinstance(body, dict) else None


@app.get("/")
def read_root():
    return {"status": "success", "message": "API is live."}


@app.get("/health")
def health_check():
    return {"status": "healthy", "system": "operational"}


@app.get("/tasks")
def list_tasks():
    return [serialize_task(row) for row in database.list_tasks()]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    row = database.get_task(task_id)
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return serialize_task(row)


@app.post("/tasks", status_code=201)
async def create_task(request: Request):
    body = await read_json(request)
    title = body.get("title") if body else None
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required"})

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)", (title.strip(), 0)
            )
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
    return serialize_task(row)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    body = await read_json(request)
    title = body.get("title") if body else None
    done = body.get("done") if body else None
    if not isinstance(title, str) or not title.strip() or type(done) is not bool:
        return JSONResponse(status_code=400, content={"error": "Invalid task"})

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
                (title.strip(), int(done), task_id),
            )
            row = (
                connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if cursor.rowcount
                else None
            )
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return serialize_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    if not cursor.rowcount:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return Response(status_code=204)
