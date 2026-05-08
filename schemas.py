# backend/schemas.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models import TaskStatus, UserRole

# --- Usuários ---

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True

# --- Tarefas ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskOut(TaskBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True