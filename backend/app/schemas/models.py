from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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
    metrics: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    perplexity: Optional[float] = None
    ai_likelihood: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None

class DetailedAnalysisResult(BaseModel):
    """文本AI检测的详细分析结果"""
    is_ai_generated: Optional[bool] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    models_results: Optional[Dict[str, Any]] = None
    # 保留原有字段，兼容旧版本
    perplexity: Optional[float] = None
    burstiness: Optional[float] = None
    style_consistency: Optional[float] = None
    ai_likelihood: Optional[str] = None
    syntax_metrics: Optional[Dict[str, Any]] = None
    coherence_metrics: Optional[Dict[str, Any]] = None
    style_metrics: Optional[Dict[str, Any]] = None

class DetectionResult(BaseModel):
    task_id: str
    status: TaskStatus
    ai_generated_percentage: Optional[float] = None
    details: Optional[List[ParagraphAnalysis]] = None
    overall_analysis: Optional[DetailedAnalysisResult] = None
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