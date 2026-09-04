from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from database import Base
 
class Users(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)