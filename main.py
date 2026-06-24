import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_FILE = "database.db"

class CreateTask(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None
    completed: bool = False

class UpdateTask(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
def create_task(task: CreateTask):
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
def update_task(task_id: int, task: UpdateTask):
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
def delete_task(task_id: int):
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
