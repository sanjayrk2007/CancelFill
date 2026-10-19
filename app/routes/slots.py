from datetime import datetime, time, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, contains_eager
from app.database import get_db
from app.dependencies import get_current_user, require_business
from app.models import Business, Slot, SlotStatus, User
from app.schemas import SlotCreate, SlotResponse, SlotUpdate
from app.services.slot_service import remove_slot, update_slot
from app.services.state_machine import NotFoundError

router = APIRouter(prefix="/slots", tags=["Slots"])

def _parse_filter_date(val: str, is_end: bool = False) -> datetime:
    raw = val.strip()
    if len(raw) == 10:
        d = datetime.strptime(raw, "%Y-%m-%d").date()
        t = time.max if is_end else time.min
        return datetime.combine(d, t).replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

@router.post("", response_model=SlotResponse, status_code=http_status.HTTP_201_CREATED, summary="Create a new time slot")
def create_slot(
    slot_in: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business)
) -> Slot:
    if slot_in.start_time.tzinfo is None:
        slot_in.start_time = slot_in.start_time.replace(tzinfo=timezone.utc)
    if slot_in.end_time.tzinfo is None:
        slot_in.end_time = slot_in.end_time.replace(tzinfo=timezone.utc)

    if slot_in.end_time <= slot_in.start_time:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be greater than start_time"
        )

    if slot_in.start_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must be in the future"
        )

    slot = Slot(
        owner_id=current_user.id,
        resource_id=slot_in.resource_id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        price=slot_in.price,
        capacity=slot_in.capacity
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

@router.get("", response_model=List[SlotResponse], summary="List all slots")
def list_slots(
    business_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="AVAILABLE"),
    include_past: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Slot]:
    query = (
        db.query(Slot)
        .join(User, Slot.owner_id == User.id)
        .outerjoin(Business, Business.user_id == User.id)
        .options(contains_eager(Slot.owner).contains_eager(User.business_profile))
    )

    if business_id:
        query = query.filter(or_(Business.id == business_id, Business.user_id == business_id, Slot.owner_id == business_id))

    if category:
        query = query.filter(func.upper(Business.category) == category.strip().upper())

    if date_from:
        try:
            start_bound = _parse_filter_date(date_from, is_end=False)
            query = query.filter(Slot.start_time >= start_bound)
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date_from format")

    if date_to:
        try:
            end_bound = _parse_filter_date(date_to, is_end=True)
            query = query.filter(Slot.start_time <= end_bound)
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date_to format")

    if not include_past:
        now = datetime.now(timezone.utc)
        query = query.filter(Slot.start_time >= now)

    status_val = (status or "AVAILABLE").strip().upper()
    if status_val == "AVAILABLE":
        query = query.filter(Slot.status == SlotStatus.AVAILABLE.value)
    elif status_val == "BOOKED":
        query = query.filter(Slot.status == SlotStatus.BOOKED.value)
    elif status_val == "HELD":
        query = query.filter(Slot.status == SlotStatus.HELD.value)
    elif status_val == "WAITLIST":
        query = query.filter(Slot.status.in_([SlotStatus.BOOKED.value, SlotStatus.HELD.value]))
    elif status_val == "ALL":
        query = query.filter(Slot.status.in_([SlotStatus.AVAILABLE.value, SlotStatus.BOOKED.value, SlotStatus.HELD.value]))
    else:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be one of AVAILABLE, BOOKED, HELD, WAITLIST, ALL",
        )

    return query.order_by(Slot.start_time.asc(), Slot.id.asc()).all()

@router.get("/{slot_id}", response_model=SlotResponse, summary="Get slot by ID")
def get_slot(
    slot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Slot:
    slot = (
        db.query(Slot)
        .join(User, Slot.owner_id == User.id)
        .outerjoin(Business, Business.user_id == User.id)
        .options(contains_eager(Slot.owner).contains_eager(User.business_profile))
        .filter(Slot.id == slot_id)
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
    return slot



@router.patch("/{slot_id}", response_model=SlotResponse, summary="Edit an unbooked slot (FR-07)")
def edit_slot(
    slot_id: str,
    slot_in: SlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> Slot:
    changes = {k: getattr(slot_in, k) for k in slot_in.model_fields_set}
    for key in ("resource_id", "start_time", "end_time", "price", "capacity"):
        if key in changes and changes[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null")
    try:
        slot = update_slot(db=db, slot_id=slot_id, owner_id=current_user.id, changes=changes)
    except NotFoundError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(e))
    return slot


@router.delete("/{slot_id}", response_model=SlotResponse, summary="Remove an unbooked slot (FR-08)")
def delete_slot(
    slot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> Slot:
    try:
        return remove_slot(db=db, slot_id=slot_id, owner_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(e))

