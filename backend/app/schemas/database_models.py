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
    overall_analysis_result = Column(String, nullable=True)  # 新的JSON格式存储所有分析结果
    
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
    ai_likelihood = Column(String, nullable=True)  # 存储AI可能性评级（高/中/低）
    metrics_data = Column(String, nullable=True)  # JSON存储所有其他指标
    
    task_id = Column(String, ForeignKey("detection_tasks.id"))
    
    task = relationship("DetectionTask", back_populates="paragraphs") 

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    channel = Column(String, index=True)  # wechat | alipay
    amount = Column(Float)
    credits = Column(Integer)
    package_type = Column(String, nullable=True)  # 套餐类型: detect_once, ai_detect_once, unlimited_1day, unlimited_1week
    status = Column(String, index=True, default="PENDING")  # PENDING | PAID | REFUNDED | CLOSED
    license_id = Column(String, ForeignKey("licenses.id"), nullable=True)
    license_token = Column(Text, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # 关联用户
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class License(Base):
    __tablename__ = "licenses"

    id = Column(String, primary_key=True, default=generate_uuid)
    token_hash = Column(String, unique=True, index=True)
    credits_remaining = Column(Integer, default=0)
    unlimited = Column(Boolean, default=False)  # 是否为不限次数套餐
    exp = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # 关联用户
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", backref="licenses")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    license_id = Column(String, ForeignKey("licenses.id"))
    delta = Column(Integer)  # 消耗的额度（负数）或返还（正数）
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)