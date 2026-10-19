"""Business-side slot management: edit and remove (FR-07, FR-08).

SRS section 3.2: edits and removals only go through while the slot is AVAILABLE, so no booking,
hold or waitlist offer is ever disrupted. A business that tries on a booked or held slot is rejected
with an explanation. Because nobody can be attached to an AVAILABLE slot, no customer notification
is needed.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Slot, SlotStatus
from app.services.state_machine import NotFoundError, assert_transition

logger = logging.getLogger(__name__)


class SlotLocked(ValueError):
    """The slot is booked, held or cancelled, so it can no longer be changed."""


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _locked_reason(slot: Slot, action: str) -> Optional[str]:
    if slot.status == SlotStatus.BOOKED.value:
        return f"This slot is booked, so it cannot be {action}. Cancel the booking first."
    if slot.status == SlotStatus.HELD.value:
        return f"This slot is temporarily held for a waitlisted customer, so it cannot be {action}."
    if slot.status == SlotStatus.CANCELLED.value:
        return f"This slot has already been removed or cancelled, so it cannot be {action}."
    return None


def _load_owned(db: Session, slot_id: str, owner_id: str) -> Slot:
    slot = db.scalars(select(Slot).where(Slot.id == slot_id).with_for_update()).first()
    if not slot:
        raise NotFoundError(f"Slot '{slot_id}' not found.")
    if slot.owner_id != owner_id:
        raise PermissionError("Not authorized to modify this slot")
    return slot


def update_slot(
    db: Session,
    slot_id: str,
    owner_id: str,
    changes: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Slot:
    """Apply a partial edit. `changes` contains only the fields the owner wants to change."""
    try:
        slot = _load_owned(db, slot_id, owner_id)
        reason = _locked_reason(slot, "edited")
        if reason:
            raise SlotLocked(reason)
        current_time = now or datetime.now(timezone.utc)
        if _aware(slot.start_time) <= current_time:
            raise SlotLocked("A slot that has already started cannot be edited.")

        new_start = _aware(changes.get("start_time", slot.start_time))
        new_end = _aware(changes.get("end_time", slot.end_time))
        if new_end <= new_start:
            raise ValueError("end_time must be greater than start_time")
        if "start_time" in changes and new_start <= current_time:
            raise ValueError("start_time must be in the future")

        if "resource_id" in changes:
            slot.resource_id = changes["resource_id"]
        slot.start_time, slot.end_time = new_start, new_end
        if "price" in changes:
            slot.price = changes["price"]
        if "capacity" in changes:
            slot.capacity = changes["capacity"]
        db.commit()
        db.refresh(slot)
        return slot
    except Exception:
        db.rollback()
        raise


def remove_slot(
    db: Session,
    slot_id: str,
    owner_id: str,
    now: Optional[datetime] = None,
) -> Slot:
    """Remove an unbooked slot. The row is kept with status CANCELLED so the business's
    slot list and booking history stay intact (FR-09)."""
    try:
        slot = _load_owned(db, slot_id, owner_id)
        reason = _locked_reason(slot, "removed")
        if reason:
            raise SlotLocked(reason)
        assert_transition("Slot", slot.status, SlotStatus.CANCELLED.value)
        slot.status = SlotStatus.CANCELLED.value
        logger.info("slot_removed slot_id=%s", slot.id)
        db.commit()
        db.refresh(slot)
        return slot
    except Exception:
        db.rollback()
        raise
