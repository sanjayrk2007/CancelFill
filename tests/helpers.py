from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Slot, SlotStatus, User


def make_slot(
    db: Session,
    owner: User,
    capacity: int = 1,
    price: str = "0.00",
    hours_ahead: float = 48,
    resource: str = "room",
) -> Slot:
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    slot = Slot(
        owner_id=owner.id, resource_id=resource, start_time=start, end_time=start + timedelta(hours=1),
        price=Decimal(price), capacity=capacity, status=SlotStatus.AVAILABLE.value,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot
