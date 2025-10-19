from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from ..utils.database import get_db
from ..services.license_service import consume_credits


router = APIRouter()


class ConsumeBody(BaseModel):
    units: int = Field(..., gt=0)
    reason: Optional[str] = None


@router.post("/usage/consume")
def consume(authorization: Optional[str] = Header(None), body: ConsumeBody = None, db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少授权令牌")
    token = authorization.split(" ", 1)[1]
    remaining = consume_credits(db, token, body.units, body.reason)
    return {"creditsRemaining": remaining}


