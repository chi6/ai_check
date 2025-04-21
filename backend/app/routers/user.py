from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..schemas.models import UserCreate, UserResponse, Token
from ..schemas.database_models import User
from ..utils.database import get_db
from ..services.auth import (
    get_user, 
    authenticate_user, 
    create_access_token, 
    get_password_hash,
    get_current_user
)
from datetime import timedelta, datetime

router = APIRouter()

@router.post("/user/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    """
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        created_at=datetime.now()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@router.post("/user/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    获取访问令牌
    """
    user = authenticate_user(db, form_data.username, form_data.password)  # 使用email作为用户名
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/user/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at
    )

@router.get("/user/tasks")
async def get_user_tasks(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的所有检测任务
    """
    tasks = []
    for task in current_user.detection_tasks:
        tasks.append({
            "id": task.id,
            "filename": task.filename,
            "status": task.status,
            "ai_generated_percentage": task.ai_generated_percentage,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        })
    
    return tasks 