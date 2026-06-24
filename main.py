import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

DB_FILE = "database.db"

class CreateTask(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None
    completed: bool = False

class UpdateTask(BaseModel):
    title: Optional[str] = None
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

