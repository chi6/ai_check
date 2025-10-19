from datetime import datetime, timedelta
import hashlib
import os
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from ..schemas.database_models import License, UsageLog


JWT_SECRET = os.getenv("JWT_SECRET", "change-me-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_license(db: Session, credits: int, device_id: Optional[str] = None, days_valid: Optional[int] = None, user_id: Optional[str] = None, unlimited: bool = False) -> str:
    """Create a JWT license token and persist its hashed mapping with credits."""
    now = datetime.utcnow()
    payload = {
        "lic": os.urandom(8).hex(),
        "cr": credits,
        "iat": int(now.timestamp()),
        "unlimited": unlimited,
    }
    if device_id:
        payload["did"] = device_id
    if days_valid and days_valid > 0:
        exp_dt = now + timedelta(days=days_valid)
        payload["exp"] = int(exp_dt.timestamp())
        exp_save = exp_dt
    else:
        exp_save = None

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    token_hash = _hash_token(token)

    license_row = License(
        token_hash=token_hash,
        credits_remaining=credits,
        unlimited=unlimited,
        exp=exp_save,
        revoked=False,
        user_id=user_id,
    )
    db.add(license_row)
    db.commit()
    db.refresh(license_row)
    return token


def get_license_status(db: Session, token: str) -> dict:
    token_hash = _hash_token(token)
    lic = db.query(License).filter(License.token_hash == token_hash).first()
    if lic is None or lic.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="许可证无效或已撤销")
    if lic.exp and lic.exp < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="许可证已过期")
    return {
        "creditsRemaining": lic.credits_remaining,
        "unlimited": lic.unlimited,
        "exp": lic.exp.isoformat() if lic.exp else None,
        "userId": lic.user_id,
    }


def consume_credits(db: Session, token: str, units: int, reason: Optional[str] = None) -> int:
    if units <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消耗单位必须为正整数")
    token_hash = _hash_token(token)
    lic = db.query(License).filter(License.token_hash == token_hash).with_for_update(nowait=False).first()
    if lic is None or lic.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="许可证无效或已撤销")
    if lic.exp and lic.exp < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="许可证已过期")
    
    # 如果是不限次数套餐，不扣除额度，但记录使用日志
    if lic.unlimited:
        log = UsageLog(license_id=lic.id, delta=0, reason=f"{reason} (不限次数套餐)")
        db.add(log)
        db.commit()
        return lic.credits_remaining
    
    if lic.credits_remaining < units:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="额度不足，请充值")

    lic.credits_remaining -= units
    log = UsageLog(license_id=lic.id, delta=-units, reason=reason)
    db.add(log)
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic.credits_remaining


def revoke_license_by_token(db: Session, token: str) -> None:
    token_hash = _hash_token(token)
    lic = db.query(License).filter(License.token_hash == token_hash).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="许可证不存在")
    if lic.revoked:
        return
    lic.revoked = True
    db.add(lic)
    db.commit()


def get_user_credits(db: Session, user_id: str) -> dict:
    """Get total credits for a user across all their licenses."""
    licenses = db.query(License).filter(
        License.user_id == user_id,
        License.revoked == False
    ).all()
    
    # 过滤出有效的许可证（未过期的）
    valid_licenses = [lic for lic in licenses if not lic.exp or lic.exp > datetime.utcnow()]
    
    # 检查是否有不限次数的套餐
    has_unlimited = any(lic.unlimited for lic in valid_licenses)
    
    # 如果有不限次数套餐，总额度设为999999表示无限
    if has_unlimited:
        total_credits = 999999
    else:
        total_credits = sum(lic.credits_remaining for lic in valid_licenses)
    
    return {
        "userId": user_id,
        "totalCredits": total_credits,
        "hasUnlimited": has_unlimited,
        "licenses": [
            {
                "id": lic.id,
                "creditsRemaining": lic.credits_remaining,
                "unlimited": lic.unlimited,
                "exp": lic.exp.isoformat() if lic.exp else None,
            }
            for lic in valid_licenses
        ]
    }


