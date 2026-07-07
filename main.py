import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

DB_FILE = "database.db"

API_TOKEN = os.environ.get("API_TOKEN")

if not API_TOKEN:
    raise RuntimeError("API_TOKEN environment variable is required")

def require_auth(authorization: str = Header(None)):
    expected_token = f"Bearer {API_TOKEN}"

    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

class CreateTask(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    completed: bool = False

class UpdateTask(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()

def create_table():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER NOT NULL DEFAULT 0)
            """
        )
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_table()
    yield

app = FastAPI(title="CRUD API", lifespan=lifespan)

def task_row(row):
    return {
        "id": row['id'],
        "title": row['title'],
        "description": row['description'],
        "completed": bool(row['completed']),
    }
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 80px auto;
                text-align: center;
            }

            a {
                display: inline-block;
                background: #2563eb;
                color: white;
                padding: 12px 20px;
                text-decoration: none;
                border-radius: 6px;
                font-size: 16px;
            }

            a:hover {
                background: #1d4ed8;
            }
        </style>
    </head>
    <body>
        <h1>Task CRUD API</h1>
        <p>Use the interactive docs page to create, view, update, and delete tasks.</p>
        <a href="/docs">Open API Docs</a>
    </body>
    </html>
    """
@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(
        completed: Optional[bool] = None,
        limit:int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    query = """
    SELECT id, title, description, completed FROM tasks
            """
    params = []

    if completed is not None:
        query += " WHERE completed = ?"
        params.append(1 if completed else 0)

    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

        return [task_row(row) for row in rows]



@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(task: CreateTask, auth: None = Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, description, completed)
            VALUES (?, ?, ?)
            """,
            (task.title, task.description, int(task.completed)),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT id, title, description, completed FROM tasks WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return task_row(row)

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: UpdateTask, auth: None = Depends(require_auth)):
    with get_db() as conn:
        existing_task = conn.execute(
            """
            SELECT id, title, description, completed FROM tasks WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        if existing_task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        title = (task.title if task.title is not None else existing_task["title"])
        description = (task.description if task.description is not None else existing_task["description"])
        completed = (int(task.completed) if task.completed is not None else existing_task["completed"])

        conn.execute(
            """
            UPDATE tasks SET title = ?, description = ?, completed = ? WHERE id = ?
            """,
            (title, description, completed, task_id,),
        )
        conn.commit()

        updated_task = conn.execute(
            """
            SELECT id, title, description, completed FROM tasks WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        return task_row(updated_task)

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, auth: None = Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.execute(
            """
            DELETE FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted"}
