import database
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


database.initialize_database()


app = FastAPI()


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
