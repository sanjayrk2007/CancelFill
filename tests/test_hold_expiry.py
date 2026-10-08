from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Hold, HoldStatus, Slot, SlotStatus, User

def test_timestamp_hold_expiry(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User
) -> None:
    now = datetime.now(timezone.utc)

    slot = Slot(
        id="expiry-slot-1",
        owner_id=business_user.id,
        resource_id="expiry_resource",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=10.0,
        status=SlotStatus.HELD.value
    )
    db.add(slot)
    db.commit()

    past_expires_at = now - timedelta(minutes=5)
    expired_hold = Hold(
        id="hold-past-1",
        slot_id=slot.id,
        user_id=customer_user.id,
        created_at=now - timedelta(minutes=20),
        expires_at=past_expires_at,
        status=HoldStatus.ACTIVE.value
    )
    db.add(expired_hold)
    db.commit()

    res = client.post(f"/api/v1/holds/{expired_hold.id}/check-expiry")
    assert res.status_code == 200
    data = res.json()

    assert data["hold_id"] == expired_hold.id
    assert data["is_expired"] is True
    assert data["status"] == "EXPIRED"
    assert data["slot_status"] == "AVAILABLE"

    db.refresh(slot)
    assert slot.status == "AVAILABLE"
