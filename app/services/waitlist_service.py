from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import WaitlistEntry, WaitlistStatus, Slot, SlotStatus

def get_waitlist_for_slot(db: Session, slot_id: str) -> List[WaitlistEntry]:
    """
    Returns active waitlist entries for a given slot, ordered by joined_at ASC.
    Earlier join time = higher priority.
    """
    return (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.slot_id == slot_id,
            WaitlistEntry.status == WaitlistStatus.WAITING.value
        )
        .order_by(WaitlistEntry.joined_at.asc())
        .all()
    )

def register_waitlist_entry(
    db: Session,
    slot_id: str,
    user_id: str,
    joined_at: Optional[datetime] = None
) -> WaitlistEntry:
    """
    Registers a user on the waitlist for a specific slot.
    """
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError(f"Slot with id '{slot_id}' not found.")

    if joined_at is None:
        joined_at = datetime.now(timezone.utc)
    elif joined_at.tzinfo is None:
        joined_at = joined_at.replace(tzinfo=timezone.utc)

    entry = WaitlistEntry(
        slot_id=slot_id,
        user_id=user_id,
        joined_at=joined_at,
        status=WaitlistStatus.WAITING.value
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
