from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
import requests
import json
import uuid
from typing import Optional
from ..utils.database import get_db
from ..schemas.database_models import User
from ..schemas.models import TokenData, UserCreate

# 扩展OAuth2PasswordBearer以支持cookie认证
class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        # 先尝试从header获取令牌
        header_authorization: str = request.headers.get("Authorization")
        if header_authorization:
            scheme, token = get_authorization_scheme_param(header_authorization)
            if scheme.lower() == "bearer":
                print(f"从Header获取到令牌: {token[:15]}...")
                return token
                
        # 如果header中没有，尝试从cookie获取
        cookie_authorization: str = request.cookies.get("access_token")
        if cookie_authorization:
            print(f"从Cookie获取到令牌: {cookie_authorization[:15]}...")
            return cookie_authorization
            
        # 如果cookie中也没有，尝试从查询参数获取
        query_token = request.query_params.get("access_token")
        if query_token:
            print(f"从查询参数获取到令牌: {query_token[:15]}...")
            return query_token
            
        # 如果都没有，记录详细日志
        print("未找到认证令牌。请求详情:")
        print(f"- 路径: {request.url.path}")
        print(f"- 客户端IP: {request.client.host if request.client else 'unknown'}")
        print(f"- 请求头: {request.headers}")
        
        # 返回原始的OAuth2PasswordBearer行为
        return await super().__call__(request)

# 配置
SECRET_KEY = os.getenv("SECRET_KEY", "af45d34a2b9584949af6be5cbb30b978fdd3b7fac3f5a8c41eac23c5c4b78902")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Google OAuth配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/google-callback")

# 微信配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

# 密码处理
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 使用支持cookie的OAuth2Bearer
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/user/token")

def verify_password(plain_password, hashed_password):
    """验证密码"""
    try:
        if not plain_password or not hashed_password:
            print(f"密码验证失败: 明文密码或哈希密码为空")
            return False
        
        # 确保哈希密码以$2b$开头（bcrypt格式）
        if not hashed_password.startswith("$2b$"):
            print(f"密码验证失败: 哈希密码格式不正确，不是bcrypt格式")
            return False
        
        result = pwd_context.verify(plain_password, hashed_password)
        if not result:
            print(f"密码验证失败: 明文密码与哈希不匹配")
        return result
    except Exception as e:
        print(f"密码验证过程中发生错误: {str(e)}")
        return False

def get_password_hash(password):
    """获取密码哈希"""
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    """通过电子邮件获取用户"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str):
    """通过ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_google_id(db: Session, google_id: str):
    """通过Google ID获取用户"""
    return db.query(User).filter(User.google_id == google_id).first()

def get_user_by_wechat_id(db: Session, wechat_open_id: str):
    """通过微信OpenID获取用户"""
    return db.query(User).filter(User.wechat_open_id == wechat_open_id).first()

def authenticate_user(db: Session, email: str, password: str):
    """验证用户"""
    user = get_user(db, email)
    if not user:
        print(f"用户验证失败: 没有找到邮箱为 {email} 的用户")
        return False
    
    # 检查是否有密码哈希
    if not user.hashed_password:
        print(f"用户验证失败: 用户 {email} 没有设置密码")
        return False
    
    # 尝试验证密码
    password_valid = verify_password(password, user.hashed_password)
    if not password_valid:
        print(f"用户验证失败: 用户 {email} 的密码验证不通过")
        return False
    
    print(f"用户验证成功: {email}")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # 计算token过期时间（秒）
    expires_in = int((expire - datetime.utcnow()).total_seconds())
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expires_in

def verify_google_token(code: str, redirect_uri: str):
    """验证Google授权码并获取用户信息"""
    # 交换授权码获取访问令牌
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    token_response = requests.post(token_url, data=token_data)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证Google授权",
        )
    
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    refresh_token = token_json.get("refresh_token")
    
    # 使用访问令牌获取用户信息
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    userinfo_response = requests.get(userinfo_url, headers=headers)
    
    if userinfo_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法获取Google用户信息",
        )
    
    userinfo = userinfo_response.json()
    return {
        "google_id": userinfo.get("sub"),
        "email": userinfo.get("email"),
        "name": userinfo.get("name"),
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def verify_wechat_code(code: str):
    """验证微信授权码并获取用户信息"""
    # 微信授权码验证URL
    access_token_url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&code={code}&grant_type=authorization_code"
    
    response = requests.get(access_token_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证微信授权",
        )
    
    result = response.json()
    if "errcode" in result and result["errcode"] != 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"微信授权失败: {result.get('errmsg', '未知错误')}",
        )
    
    access_token = result.get("access_token")
    open_id = result.get("openid")
    union_id = result.get("unionid")
    
    # 获取用户信息
    userinfo_url = f"https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={open_id}&lang=zh_CN"
    userinfo_response = requests.get(userinfo_url)
    
    if userinfo_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法获取微信用户信息",
        )
    
    userinfo = userinfo_response.json()
    return {
        "open_id": open_id,
        "union_id": union_id,
        "nickname": userinfo.get("nickname"),
        "headimgurl": userinfo.get("headimgurl"),
    }

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError as e:
        raise credentials_exception
    
    user = get_user_by_id(db, token_data.user_id)
    if user is None:
        # 删除访客用户逻辑，直接返回错误
        raise credentials_exception
    
    return user 