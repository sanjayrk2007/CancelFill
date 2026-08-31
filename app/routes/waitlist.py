from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import WaitlistCreate, WaitlistResponse
from app.services.waitlist_service import register_waitlist_entry, get_waitlist_for_slot

router = APIRouter(tags=["Waitlist"])

@router.post("/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED, summary="Register customer on waitlist")
def add_to_waitlist(entry_in: WaitlistCreate, db: Session = Depends(get_db)):
    """
    Registers a customer on the waitlist for a specific slot.
    """
    try:
        entry = register_waitlist_entry(
            db=db,
            slot_id=entry_in.slot_id,
            user_id=entry_in.user_id,
            joined_at=entry_in.joined_at
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/slots/{slot_id}/waitlist", response_model=List[WaitlistResponse], summary="View waitlist for slot ordered by priority")
def view_slot_waitlist(slot_id: str, db: Session = Depends(get_db)):
    """
    Returns active waitlist entries for a slot ordered by join time (earlier join time = higher priority).
    """
    entries = get_waitlist_for_slot(db=db, slot_id=slot_id)
    response_entries = []
    for idx, entry in enumerate(entries, start=1):
        res = WaitlistResponse.model_validate(entry)
        res.priority_order = idx
        response_entries.append(res)
    return response_entries
