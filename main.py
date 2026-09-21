import os
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI


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


@app.get("/")
def read_root():
    return {"status": "success", "message": "API is live."}


@app.get("/health")
def health_check():
    return {"status": "healthy", "system": "operational"}
