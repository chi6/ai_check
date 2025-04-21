from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from typing import Optional
from ..utils.database import get_db
from ..schemas.database_models import User
from ..schemas.models import TokenData

# 配置
SECRET_KEY = os.getenv("SECRET_KEY", "af45d34a2b9584949af6be5cbb30b978fdd3b7fac3f5a8c41eac23c5c4b78902")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 密码处理
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/user/token")

def verify_password(plain_password, hashed_password):
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """获取密码哈希"""
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    """通过电子邮件获取用户"""
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    """验证用户"""
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户"""
    # 跳过令牌验证，直接返回一个默认的访客用户
    # 检查数据库中是否已有访客用户，如果没有则创建一个
    guest_user = db.query(User).filter(User.email == "guest@example.com").first()
    
    if guest_user is None:
        # 创建一个新的访客用户
        guest_user = User(
            id="guest-user",
            email="guest@example.com",
            username="访客用户",
            hashed_password=get_password_hash("guestpassword"),
            created_at=datetime.utcnow()
        )
        db.add(guest_user)
        db.commit()
        db.refresh(guest_user)
    
    return guest_user 