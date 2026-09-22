import os
import database

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions
from fastapi.responses import JSONResponse, Response


load_dotenv()
if os.environ.get("FLYRANK_SKIP_DB_INIT") != "1":
    database.initialize_database()


app = FastAPI()
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=SyncClientOptions(auto_refresh_token=False, persist_session=False),
)
bearer_auth = HTTPBearer(auto_error=False, scheme_name="BearerAuth", bearerFormat="JWT")


class AuthFailure(Exception):
    def __init__(self, message, status_code=401):
        self.message = message
        self.status_code = status_code


@app.exception_handler(AuthFailure)
async def auth_failure_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


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

    row = database.create_task(title.strip())
    return serialize_task(row)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    body = await read_json(request)
    title = body.get("title") if body else None
    done = body.get("done") if body else None
    if not isinstance(title, str) or not title.strip() or type(done) is not bool:
        return JSONResponse(status_code=400, content={"error": "Invalid task"})

    row = database.update_task(task_id, title.strip(), done)
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return serialize_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not database.delete_task(task_id):
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return Response(status_code=204)
