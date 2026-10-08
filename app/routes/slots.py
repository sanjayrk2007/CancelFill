from datetime import timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_business
from app.models import Slot, User
from app.schemas import SlotCreate, SlotResponse

router = APIRouter(prefix="/slots", tags=["Slots"])

@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED, summary="Create a new time slot")
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be greater than start_time"
        )

    slot = Slot(
        owner_id=current_user.id,
        resource_id=slot_in.resource_id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        price=slot_in.price
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

@router.get("", response_model=List[SlotResponse], summary="List all slots")
def list_slots(db: Session = Depends(get_db)) -> List[Slot]:
    return db.query(Slot).all()

@router.get("/{slot_id}", response_model=SlotResponse, summary="Get slot by ID")
def get_slot(slot_id: str, db: Session = Depends(get_db)) -> Slot:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
    return slot
