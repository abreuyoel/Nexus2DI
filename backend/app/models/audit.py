from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "AUDIT_LOG"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True, index=True)
    rol = Column(String(50), nullable=True)
    ip_address = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True)
    entity_name = Column(String(500), nullable=True)
    changes = Column(Text, nullable=True)
    status = Column(String(20), default="OK", nullable=False)
