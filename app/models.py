from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    original_request = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    priority = Column(String(50), nullable=True)
    deadline = Column(String(100), nullable=True)
    missing_information = Column(Text, nullable=True)
    status = Column(String(50), default="RECEIVED")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    actions = relationship(
        "ActionItem",
        back_populates="work_item",
        cascade="all, delete-orphan"
    )

    activities = relationship(
        "ActivityLog",
        back_populates="work_item",
        cascade="all, delete-orphan"
    )


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(
        Integer,
        ForeignKey("work_items.id"),
        nullable=False
    )
    description = Column(Text, nullable=False)
    action_type = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    automatable = Column(Boolean, default=False)
    tool_name = Column(String(100), nullable=True)
    tool_params = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING")
    output = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    work_item = relationship(
        "WorkItem",
        back_populates="actions"
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(
        Integer,
        ForeignKey("work_items.id"),
        nullable=False
    )
    event = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    work_item = relationship(
        "WorkItem",
        back_populates="activities"
    )