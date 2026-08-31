from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models import SlotStatus, WaitlistStatus, HoldStatus, BookingStatus

# --- SLOT SCHEMAS ---
class SlotCreate(BaseModel):
    resource_id: str = Field(..., json_schema_extra={"example": "room_101"})
    start_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T10:00:00Z"})
    end_time: datetime = Field(..., json_schema_extra={"example": "2026-09-01T11:00:00Z"})

class SlotResponse(BaseModel):
    id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    status: SlotStatus

    model_config = ConfigDict(from_attributes=True)

# --- WAITLIST SCHEMAS ---
class WaitlistCreate(BaseModel):
    slot_id: str = Field(..., json_schema_extra={"example": "slot_uuid_123"})
    user_id: str = Field(..., json_schema_extra={"example": "user_customer_a"})
    joined_at: Optional[datetime] = Field(None, json_schema_extra={"example": "2026-09-01T09:00:00Z"})

class WaitlistResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    joined_at: datetime
    status: WaitlistStatus
    priority_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# --- BOOKING SCHEMAS ---
class BookingCreate(BaseModel):
    slot_id: str = Field(..., json_schema_extra={"example": "slot_uuid_123"})
    user_id: str = Field(..., json_schema_extra={"example": "user_initial_booker"})

class BookingResponse(BaseModel):
    id: str
    slot_id: str
    user_id: str
    booked_at: datetime
    status: BookingStatus

    model_config = ConfigDict(from_attributes=True)

# --- HOLD SCHEMAS ---
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

# --- CANCELLATION WORKFLOW RESPONSE ---
class CancellationResultResponse(BaseModel):
    booking_id: str
    booking_status: BookingStatus
    slot_id: str
    slot_status: SlotStatus
    candidate_selected: bool
    selected_user_id: Optional[str] = None
    hold: Optional[HoldResponse] = None
    message: str
