# backend/main.py

from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

import models, schemas, auth, database
from database import engine, get_db

# Configuração de Logs (Requisito RF08)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria as tabelas no banco de dados automaticamente ao iniciar
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskManager API", version="1.0.0")

# --- Rotas de Autenticação (RF01, RF02) ---

@app.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"New user registered: {user.email}")
    return new_user

@app.post("/token")
def login_for_access_token(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Rotas de Tarefas (RF03, RF04, RF05) ---

@app.post("/tasks", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    new_task = models.Task(**task.model_dump(), owner_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.get("/tasks", response_model=List[schemas.TaskOut])
def get_tasks(
    skip: int = 0, 
    limit: int = 10, 
    status: Optional[models.TaskStatus] = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.Task)
    
    # Filtro: Usuário comum vê só as suas, Admin vê todas (opcional, aqui deixamos o dono ver as suas)
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(models.Task.owner_id == current_user.id)
    
    if status:
        query = query.filter(models.Task.status == status)
        
    return query.offset(skip).limit(limit).all()

@app.put("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Regra: Somente o dono ou Admin pode atualizar
    if db_task.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")
    
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(db_task, key, value)
        
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Requisito RF05: Apenas administradores podem excluir registros (ou o dono, dependendo da sua interpretação)
    # Aqui vamos seguir a regra estrita do seu documento: "Apenas administradores podem excluir registros"
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete tasks")
        
    db.delete(db_task)
    db.commit()
    return {"detail": "Task deleted successfully"}

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000"],  # ajuste se seu frontend estiver em outro lugar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)