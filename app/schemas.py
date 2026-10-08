from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models import SlotStatus, WaitlistStatus, HoldStatus, BookingStatus, BookingSource, UserRole

class UserRegister(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    password: str = Field(..., json_schema_extra={"example": "password123"})
    name: str = Field(..., json_schema_extra={"example": "Alice"})
    role: UserRole = Field(default=UserRole.CUSTOMER, json_schema_extra={"example": "CUSTOMER"})

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

    model_config = ConfigDict(from_attributes=True)

class SlotCreate(BaseModel):
    resource_id: str = Field(..., json_schema_extra={"example": "room_101"})
    start_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T10:00:00Z"})
    end_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T11:00:00Z"})
    price: Decimal = Field(default=Decimal("0.00"), json_schema_extra={"example": "50.00"})

class SlotResponse(BaseModel):
    id: str
    owner_id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    status: SlotStatus

    model_config = ConfigDict(from_attributes=True)

class WaitlistCreate(BaseModel):
    slot_id: str = Field(..., json_schema_extra={"example": "slot_uuid_123"})
    joined_at: Optional[datetime] = Field(None, json_schema_extra={"example": "2026-09-01T09:00:00Z"})

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

    model_config = ConfigDict(from_attributes=True)

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


class BusinessSlotResponse(BaseModel):
    id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    status: SlotStatus
    price: Decimal
    waitlist_count: int
    active_booking_id: Optional[str] = None
    active_booking_holder_name: Optional[str] = None
    active_hold_holder_name: Optional[str] = None
    active_hold_expires_at: Optional[datetime] = None


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
    slot_price: Decimal
