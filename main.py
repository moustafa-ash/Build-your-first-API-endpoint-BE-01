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


def serialize_user(user):
    if hasattr(user, "model_dump"):
        user = user.model_dump(mode="json")
    elif hasattr(user, "dict"):
        user = user.dict()
    elif not isinstance(user, dict):
        user = vars(user)
    return {
        key: user.get(key)
        for key in ("id", "email", "created_at")
        if user.get(key) is not None
    }


def provider_unavailable(exc):
    return isinstance(exc, (httpx.RequestError, TimeoutError)) or getattr(exc, "status", 0) >= 500


async def read_json(request):
    try:
        body = await request.json()
    except Exception:
        return None
    return body if isinstance(body, dict) else None


@app.post("/auth/signup", status_code=201)
async def signup(request: Request):
    body = await read_json(request)
    email = body.get("email") if body else None
    password = body.get("password") if body else None
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})
    try:
        response = supabase.auth.sign_up({"email": email.strip(), "password": password})
    except Exception as exc:
        if provider_unavailable(exc):
            return JSONResponse(status_code=503, content={"error": "Authentication service unavailable"})
        return JSONResponse(status_code=400, content={"error": "Sign up failed"})
    if getattr(response, "user", None) is None:
        return JSONResponse(status_code=400, content={"error": "Sign up failed"})
    return serialize_user(response.user)


@app.post("/auth/login")
async def login(request: Request):
    body = await read_json(request)
    email = body.get("email") if body else None
    password = body.get("password") if body else None
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
    except Exception as exc:
        if provider_unavailable(exc):
            return JSONResponse(status_code=503, content={"error": "Authentication service unavailable"})
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})
    session = getattr(response, "session", None)
    if session is None or not getattr(session, "access_token", None):
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }


def require_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_auth),
):
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthFailure("Access token required")
    return credentials.credentials


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_auth),
):
    token = require_bearer(credentials)
    try:
        response = supabase.auth.get_user(token)
    except Exception as exc:
        if provider_unavailable(exc):
            raise AuthFailure("Authentication service unavailable", 503) from exc
        raise AuthFailure("Invalid or expired token") from exc
    user = getattr(response, "user", None)
    if user is None:
        raise AuthFailure("Invalid or expired token")
    return {"token": token, "user": user}


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(auth=Depends(current_user)):
    return serialize_user(auth["user"])


@app.get("/protected/dashboard")
def protected_dashboard(auth=Depends(current_user)):
    user = serialize_user(auth["user"])
    return {"message": "Welcome to your dashboard", "user_id": user.get("id")}


@app.post("/auth/logout", status_code=204)
def logout(auth=Depends(current_user)):
    try:
        response = httpx.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {auth['token']}",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise AuthFailure("Authentication service unavailable", 503) from exc
    if response.status_code >= 500:
        raise AuthFailure("Authentication service unavailable", 503)
    if response.status_code >= 400:
        raise AuthFailure("Invalid or expired token")
    return Response(status_code=204)


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
