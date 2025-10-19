from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..utils.database import get_db
from ..services.license_service import get_license_status


router = APIRouter()


@router.get("/license")
def get_license(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少授权令牌")
    token = authorization.split(" ", 1)[1]
    return get_license_status(db, token)


