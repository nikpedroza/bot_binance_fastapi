from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, ) #AYUDA AYUDA