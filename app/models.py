import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Index, text, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    BUSINESS = "BUSINESS"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    HELD = "HELD"

class WaitlistStatus(str, enum.Enum):
    WAITING = "WAITING"
    OFFERED = "OFFERED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"

class HoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"

class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class BookingSource(str, enum.Enum):
    DIRECT = "DIRECT"
    RECOVERED = "RECOVERED"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.CUSTOMER.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("status IN ('AVAILABLE', 'BOOKED', 'HELD')", name="ck_slot_status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default=SlotStatus.AVAILABLE.value)

    owner = relationship("User", foreign_keys=[owner_id])
    waitlist_entries = relationship("WaitlistEntry", back_populates="slot", cascade="all, delete-orphan")
    holds = relationship("Hold", back_populates="slot", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="slot", cascade="all, delete-orphan")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        Index(
            "uq_active_waitlist_per_slot_user",
            "slot_id",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('WAITING', 'OFFERED')"),
            sqlite_where=text("status IN ('WAITING', 'OFFERED')")
        ),
        CheckConstraint("status IN ('WAITING', 'OFFERED', 'CANCELLED', 'EXPIRED', 'CONFIRMED', 'DECLINED')", name="ck_waitlist_status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default=WaitlistStatus.WAITING.value)

    slot = relationship("Slot", back_populates="waitlist_entries")
    user = relationship("User", foreign_keys=[user_id])

class Hold(Base):
    __tablename__ = "holds"
    __table_args__ = (
        Index(
            "uq_active_hold_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'")
        ),
        CheckConstraint("status IN ('ACTIVE', 'EXPIRED', 'RELEASED', 'CONFIRMED', 'DECLINED')", name="ck_hold_status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default=HoldStatus.ACTIVE.value)

    slot = relationship("Slot", back_populates="holds")
    user = relationship("User", foreign_keys=[user_id])

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_confirmed_booking_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'CONFIRMED'"),
            sqlite_where=text("status = 'CONFIRMED'")
        ),
        CheckConstraint("status IN ('CONFIRMED', 'CANCELLED')", name="ck_booking_status"),
        CheckConstraint("source IN ('DIRECT', 'RECOVERED')", name="ck_booking_source"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default=BookingStatus.CONFIRMED.value)
    source = Column(String(50), nullable=False, default=BookingSource.DIRECT.value)
    recovered_from_booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)

    slot = relationship("Slot", back_populates="bookings")
    user = relationship("User", foreign_keys=[user_id])
