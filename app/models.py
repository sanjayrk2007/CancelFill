import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Index, Text, text, CheckConstraint, Integer, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    BUSINESS = "BUSINESS"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    HELD = "HELD"
    CANCELLED = "CANCELLED"

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

class HoldKind(str, enum.Enum):
    OFFER = "OFFER"        # waitlist offer created after a cancellation
    CHECKOUT = "CHECKOUT"  # seat reserved while a direct booking is being paid for

class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    REFUND_FAILED = "REFUND_FAILED"

class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.CUSTOMER.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    phone = Column(String(32), nullable=True)
    notify_email = Column(Boolean, nullable=False, default=True)
    notify_sms = Column(Boolean, nullable=False, default=True)
    notify_push = Column(Boolean, nullable=False, default=True)

class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("status IN ('AVAILABLE', 'BOOKED', 'HELD', 'CANCELLED')", name="ck_slot_status"),
        CheckConstraint("capacity >= 1", name="ck_slot_capacity"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    # Descriptive only (FR-06): how many people the slot accommodates. A slot is still ONE bookable
    # unit: it has at most one confirmed booking and one active hold (NFR-03, SRS section 8).
    capacity = Column(Integer, nullable=False, default=1, server_default="1")
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
        CheckConstraint("kind IN ('OFFER', 'CHECKOUT')", name="ck_hold_kind"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default=HoldStatus.ACTIVE.value)
    kind = Column(String(20), nullable=False, default=HoldKind.OFFER.value, server_default="OFFER")

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
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_role = Column(String(50), nullable=True)

    slot = relationship("Slot", back_populates="bookings")
    user = relationship("User", foreign_keys=[user_id])



class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)


class PushSubscription(Base):
    """A browser Web Push subscription belonging to a user."""
    __tablename__ = "push_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Notification(Base):
    """User-facing message. Outbound email/SMS/push attempts hang off it as deliveries."""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)
    show_in_app = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime(timezone=True), nullable=True)

    deliveries = relationship("NotificationDelivery", back_populates="notification", cascade="all, delete-orphan")


class NotificationDelivery(Base):
    """One outbound attempt-set for one channel. Acts as a transactional outbox row."""
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        CheckConstraint("channel IN ('EMAIL', 'SMS', 'PUSH')", name="ck_delivery_channel"),
        CheckConstraint("status IN ('PENDING', 'SENT', 'FAILED')", name="ck_delivery_status"),
        Index("ix_delivery_pending", "status", "next_attempt_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String(36), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(10), nullable=False)
    destination = Column(Text, nullable=False)  # email address, phone number, or push subscription id
    status = Column(String(10), nullable=False, default=DeliveryStatus.PENDING.value)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    notification = relationship("Notification", back_populates="deliveries")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'PAID', 'FAILED', 'EXPIRED', 'REFUND_PENDING', 'REFUNDED', 'REFUND_FAILED')",
            name="ck_payment_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = Column(String(36), ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True)
    hold_id = Column(String(36), ForeignKey("holds.id", ondelete="SET NULL"), nullable=True, index=True)
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    provider = Column(String(20), nullable=False)
    provider_order_id = Column(String(100), nullable=False, unique=True)
    provider_payment_id = Column(String(100), nullable=True, unique=True)
    status = Column(String(20), nullable=False, default=PaymentStatus.CREATED.value)
    refund_id = Column(String(100), nullable=True)
    refund_reason = Column(Text, nullable=True)
    refund_attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    paid_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    slot = relationship("Slot", foreign_keys=[slot_id])
    user = relationship("User", foreign_keys=[user_id])
