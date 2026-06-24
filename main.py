import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import
from pydantic import BaseModel, Field

DB_FILE = "database.db"

class CreateTask(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None
    completed: bool = False

class UpdateTask(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


