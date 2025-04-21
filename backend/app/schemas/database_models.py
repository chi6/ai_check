from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..utils.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    
    detection_tasks = relationship("DetectionTask", back_populates="owner")

class DetectionTask(Base):
    __tablename__ = "detection_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String)
    file_size = Column(Integer)
    status = Column(String)
    ai_generated_percentage = Column(Float, nullable=True)
    
    # 添加整体分析结果
    overall_perplexity = Column(Float, nullable=True)
    overall_burstiness = Column(Float, nullable=True)
    overall_syntax_analysis = Column(String, nullable=True)  # JSON存储
    overall_coherence_analysis = Column(String, nullable=True)  # JSON存储
    overall_style_analysis = Column(String, nullable=True)  # JSON存储
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(String, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="detection_tasks")
    paragraphs = relationship("ParagraphResult", back_populates="task")

class ParagraphResult(Base):
    __tablename__ = "paragraph_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    paragraph = Column(Text)
    ai_generated = Column(Boolean)
    reason = Column(String)
    
    # 添加详细指标
    perplexity = Column(Float, nullable=True)
    burstiness = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    metrics_data = Column(String, nullable=True)  # JSON存储所有其他指标
    
    task_id = Column(String, ForeignKey("detection_tasks.id"))
    
    task = relationship("DetectionTask", back_populates="paragraphs") 