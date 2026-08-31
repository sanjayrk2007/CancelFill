import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base

class SlotStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    HELD = "HELD"

class WaitlistStatus(str, enum.Enum):
    WAITING = "WAITING"
    OFFERED = "OFFERED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class HoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    CONFIRMED = "CONFIRMED"

class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class Slot(Base):
    __tablename__ = "slots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default=SlotStatus.AVAILABLE.value)

    waitlist_entries = relationship("WaitlistEntry", back_populates="slot", cascade="all, delete-orphan")
    holds = relationship("Hold", back_populates="slot", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="slot", cascade="all, delete-orphan")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default=WaitlistStatus.WAITING.value)

    slot = relationship("Slot", back_populates="waitlist_entries")

class Hold(Base):
    __tablename__ = "holds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default=HoldStatus.ACTIVE.value)

    slot = relationship("Slot", back_populates="holds")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    booked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default=BookingStatus.CONFIRMED.value)

    slot = relationship("Slot", back_populates="bookings")
