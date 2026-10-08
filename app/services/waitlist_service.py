from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import WaitlistEntry
from app.services.allocation_service import get_waitlist_for_slot, join_waitlist

def register_waitlist_entry(
    db: Session,
    slot_id: str,
    user_id: str,
    joined_at: Optional[datetime] = None
) -> WaitlistEntry:
    return join_waitlist(db=db, slot_id=slot_id, user_id=user_id, joined_at=joined_at)
