from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ParagraphAnalysis(BaseModel):
    paragraph: str
    ai_generated: bool
    reason: str

class DetectionResult(BaseModel):
    task_id: str
    status: TaskStatus
    ai_generated_percentage: Optional[float] = None
    details: Optional[List[ParagraphAnalysis]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UploadResponse(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.UPLOADED
    filename: str
    file_size: int
    created_at: datetime = Field(default_factory=datetime.now)

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None 