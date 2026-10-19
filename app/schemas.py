import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models import (
    SlotStatus, WaitlistStatus, HoldStatus, BookingStatus, BookingSource, UserRole, PaymentStatus, BusinessCategory
)

def _clean_and_validate_phone(v: Optional[str], field_name: str) -> str:
    if not v or not v.strip():
        raise ValueError(f"{field_name} is required")
    cleaned = v.strip()
    digits = re.sub(r"\D", "", cleaned)
    if not (10 <= len(digits) <= 15) or not re.fullmatch(r"\+?[1-9]\d{9,14}", cleaned):
        raise ValueError(f"{field_name} must be a valid phone number with 10-15 digits, e.g. +919876543210")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned

class UserRegister(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    password: str = Field(..., json_schema_extra={"example": "password123"})
    name: str = Field(..., json_schema_extra={"example": "Alice"})
    role: UserRole = Field(default=UserRole.CUSTOMER, json_schema_extra={"example": "CUSTOMER"})
    phone: Optional[str] = None
    business_name: Optional[str] = None
    category: Optional[BusinessCategory] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    @model_validator(mode="after")
    def _validate_role_fields(self) -> "UserRegister":
        if self.role == UserRole.CUSTOMER:
            self.phone = _clean_and_validate_phone(self.phone, "Phone")
        elif self.role == UserRole.BUSINESS:
            if not self.business_name or not self.business_name.strip():
                raise ValueError("Business name is required for business registration")
            if not self.category:
                raise ValueError("Business category is required for business registration")
            self.contact_phone = _clean_and_validate_phone(self.contact_phone, "Contact phone")
            if not self.phone and self.contact_phone:
                self.phone = self.contact_phone
        return self

class UserLogin(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    password: str = Field(..., json_schema_extra={"example": "password123"})

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    created_at: datetime
    phone: Optional[str] = None
    notify_email: bool = True
    notify_sms: bool = True
    notify_push: bool = True
    business_name: Optional[str] = None
    category: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: Optional[str] = Field(default=None, min_length=1, max_length=60, json_schema_extra={"example": "Alice"})
    phone: Optional[str] = Field(default=None, max_length=32, json_schema_extra={"example": "+919876543210"})
    notify_email: Optional[bool] = None
    notify_sms: Optional[bool] = None
    notify_push: Optional[bool] = None
    business_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[BusinessCategory] = None
    contact_phone: Optional[str] = Field(default=None, max_length=32)
    contact_address: Optional[str] = None

    @field_validator("phone", "contact_phone")
    @classmethod
    def _valid_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        cleaned = v.strip()
        if not re.fullmatch(r"\+[1-9]\d{7,14}", cleaned):
            raise ValueError("Phone must be in international format, e.g. +919876543210")
        return cleaned

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)

class MessageResponse(BaseModel):
    message: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class CustomerStatsResponse(BaseModel):
    total_bookings: int
    upcoming_bookings: int
    recovered_bookings: int
    cancelled_bookings: int
    offers_received: int
    offers_accepted: int
    offers_declined: int
    offers_expired: int
    acceptance_rate: float
    active_waitlist_entries: int
class SlotCreate(BaseModel):
    resource_id: str = Field(..., json_schema_extra={"example": "room_101"})
    start_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T10:00:00Z"})
    end_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T11:00:00Z"})
    price: Decimal = Field(default=Decimal("0.00"), json_schema_extra={"example": "50.00"})
    capacity: int = Field(default=1, ge=1, le=10000, json_schema_extra={"example": 1})

class SlotUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    resource_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    capacity: Optional[int] = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def _at_least_one(self) -> "SlotUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self

class SlotResponse(BaseModel):
    id: str
    owner_id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    capacity: int = 1
    status: SlotStatus

    model_config = ConfigDict(from_attributes=True)

class WaitlistCreate(BaseModel):
    slot_id: str = Field(..., json_schema_extra={"example": "slot_uuid_123"})

class WaitlistResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    joined_at: datetime
    status: WaitlistStatus
    priority_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class BookingCreate(BaseModel):
    slot_id: str = Field(..., json_schema_extra={"example": "slot_uuid_123"})

class BookingResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    booked_at: datetime
    status: BookingStatus
    source: BookingSource = BookingSource.DIRECT
    recovered_from_booking_id: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CancelBookingRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: Optional[str] = Field(default=None, max_length=500)

class HoldResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    status: HoldStatus

    model_config = ConfigDict(from_attributes=True)

class HoldExpiryCheckResponse(BaseModel):
    hold_id: str
    status: HoldStatus
    is_expired: bool
    expires_at: datetime
    checked_at: datetime
    slot_id: str
    slot_status: SlotStatus
    message: str

class CancellationResultResponse(BaseModel):
    booking_id: str
    booking_status: BookingStatus
    slot_id: str
    slot_status: SlotStatus
    candidate_selected: bool
    selected_user_id: Optional[str] = None
    hold: Optional[HoldResponse] = None
    message: str


class MyOfferResponse(HoldResponse):
    slot: SlotResponse
    seconds_remaining: int


class MyBookingResponse(BookingResponse):
    slot: SlotResponse
    payment_status: Optional[PaymentStatus] = None


class MyWaitlistEntryResponse(WaitlistResponse):
    slot: SlotResponse


class BusinessStatsResponse(BaseModel):
    total_slots: int
    booked_slots: int
    utilization_rate: float
    cancellations: int
    offers_made: int
    offers_accepted: int
    offers_declined: int
    offers_expired: int
    conversion_rate: float
    recovered_bookings: int
    recovered_revenue: Decimal


class BookingHolder(BaseModel):
    booking_id: str
    name: str


class BusinessSlotResponse(BaseModel):
    id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    status: SlotStatus
    price: Decimal
    capacity: int = 1
    waitlist_count: int
    # First booking/hold are kept for backwards compatibility with single-seat views.
    active_booking_id: Optional[str] = None
    active_booking_holder_name: Optional[str] = None
    active_hold_holder_name: Optional[str] = None
    active_hold_expires_at: Optional[datetime] = None
    booking_holders: List[BookingHolder] = []


class BusinessWaitlistEntryResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    joined_at: datetime
    status: WaitlistStatus
    position: Optional[int] = None


class BusinessWaitlistSlotResponse(BaseModel):
    slot_id: str
    resource_id: str
    entries: List[BusinessWaitlistEntryResponse]


class BusinessBookingResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    holder_name: str
    booked_at: datetime
    status: BookingStatus
    source: BookingSource
    recovered_from_booking_id: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_role: Optional[str] = None
    slot_price: Decimal



class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    link: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    unread_count: int
    items: List[NotificationResponse]


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=10)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushConfigResponse(BaseModel):
    enabled: bool
    public_key: Optional[str] = None


class PaymentConfigResponse(BaseModel):
    enabled: bool
    provider: str
    key_id: Optional[str] = None
    currency: str


class CheckoutRequest(BaseModel):
    slot_id: Optional[str] = None
    hold_id: Optional[str] = None


class CheckoutResponse(BaseModel):
    payment_id: str
    hold_id: str
    provider: str
    key_id: str
    provider_order_id: str
    amount: Decimal
    amount_minor: int
    currency: str
    expires_at: datetime


class ConfirmPaymentRequest(BaseModel):
    payment_id: str
    provider_order_id: str
    provider_payment_id: str
    signature: str


class MockPaymentResponse(BaseModel):
    provider_order_id: str
    provider_payment_id: str
    signature: str


class PaymentResponse(BaseModel):
    id: str
    slot_id: str
    booking_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    refund_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BusinessPaymentResponse(PaymentResponse):
    customer_name: str
    resource_id: str
