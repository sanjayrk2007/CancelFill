from typing import Dict
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Hold, HoldStatus, Slot, SlotStatus, User

def test_timestamp_hold_expiry(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    customer_auth_headers: Dict[str, str]
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

    res = client.post(f"/api/v1/holds/{expired_hold.id}/check-expiry", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["hold_id"] == expired_hold.id
    assert data["is_expired"] is True
    assert data["status"] == "EXPIRED"
    assert data["slot_status"] == "AVAILABLE"

    db.refresh(slot)
    assert slot.status == "AVAILABLE"

def test_check_expiry_unauthenticated(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        id="expiry-slot-unauth",
        owner_id=business_user.id,
        resource_id="expiry_resource_unauth",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=10.0,
        status=SlotStatus.HELD.value
    )
    db.add(slot)
    db.commit()

    hold = Hold(
        id="hold-unauth-1",
        slot_id=slot.id,
        user_id=customer_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold)
    db.commit()

    res = client.post(f"/api/v1/holds/{hold.id}/check-expiry")
    assert res.status_code == 401

def test_check_expiry_unrelated_user_forbidden(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    other_customer_auth_headers: Dict[str, str],
    other_business_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        id="expiry-slot-forbidden",
        owner_id=business_user.id,
        resource_id="expiry_resource_forbidden",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=10.0,
        status=SlotStatus.HELD.value
    )
    db.add(slot)
    db.commit()

    hold = Hold(
        id="hold-forbidden-1",
        slot_id=slot.id,
        user_id=customer_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold)
    db.commit()

    res_cust = client.post(f"/api/v1/holds/{hold.id}/check-expiry", headers=other_customer_auth_headers)
    assert res_cust.status_code == 403

    res_biz = client.post(f"/api/v1/holds/{hold.id}/check-expiry", headers=other_business_auth_headers)
    assert res_biz.status_code == 403

def test_check_expiry_slot_owner_authorized(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    business_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        id="expiry-slot-slotowner",
        owner_id=business_user.id,
        resource_id="expiry_resource_slotowner",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=10.0,
        status=SlotStatus.HELD.value
    )
    db.add(slot)
    db.commit()

    hold = Hold(
        id="hold-slotowner-1",
        slot_id=slot.id,
        user_id=customer_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold)
    db.commit()

    res = client.post(f"/api/v1/holds/{hold.id}/check-expiry", headers=business_auth_headers)
    assert res.status_code == 200
