from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Slot
from app.schemas import SlotCreate, SlotResponse

router = APIRouter(prefix="/slots", tags=["Slots"])

@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED, summary="Create a new time slot")
def create_slot(slot_in: SlotCreate, db: Session = Depends(get_db)):
    """
    Creates a new resource slot in the system.
    """
    if slot_in.start_time.tzinfo is None:
        slot_in.start_time = slot_in.start_time.replace(tzinfo=slot_in.start_time.tzinfo)
    if slot_in.end_time.tzinfo is None:
        slot_in.end_time = slot_in.end_time.replace(tzinfo=slot_in.end_time.tzinfo)

    slot = Slot(
        resource_id=slot_in.resource_id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

@router.get("", response_model=List[SlotResponse], summary="List all slots")
def list_slots(db: Session = Depends(get_db)):
    """
    Returns a list of all slots.
    """
    return db.query(Slot).all()

@router.get("/{slot_id}", response_model=SlotResponse, summary="Get slot by ID")
def get_slot(slot_id: str, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific slot.
    """
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
    return slot
