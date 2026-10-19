from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Business, Slot, SlotStatus, User

def test_create_and_get_slot(client: TestClient, db: Session, business_auth_headers: Dict[str, str]) -> None:
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(hours=1)).isoformat()
    end_time = (now + timedelta(hours=2)).isoformat()

    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_room_101",
            "start_time": start_time,
            "end_time": end_time,
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == "test_room_101"
    assert data["status"] == "AVAILABLE"
    assert data["price"] == "50.00"
    assert "owner_id" in data
    slot_id = data["id"]

    list_response = client.get("/api/v1/slots", headers=business_auth_headers)
    assert list_response.status_code == 200
    slots = list_response.json()
    assert len(slots) == 1
    assert slots[0]["id"] == slot_id

    get_res = client.get(f"/api/v1/slots/{slot_id}", headers=business_auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == slot_id

    slot = db.query(Slot).filter(Slot.id == slot_id).one()
    assert slot.id == slot_id

def test_create_slot_naive_datetime(client: TestClient, business_auth_headers: Dict[str, str]) -> None:
    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "room_naive_tz",
            "start_time": "2027-09-01T10:00:00",
            "end_time": "2027-09-01T11:00:00",
            "price": "25.50"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == "room_naive_tz"
    assert data["price"] == "25.50"

def test_create_slot_end_time_before_start_time(client: TestClient, business_auth_headers: Dict[str, str]) -> None:
    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "invalid_time_room",
            "start_time": "2027-09-01T12:00:00Z",
            "end_time": "2027-09-01T11:00:00Z",
            "price": "10.00"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 422

def test_create_slot_auth_gates(
    client: TestClient,
    customer_auth_headers: Dict[str, str]
) -> None:
    payload = {
        "resource_id": "room_auth",
        "start_time": "2027-09-01T10:00:00Z",
        "end_time": "2027-09-01T11:00:00Z",
        "price": "10.00"
    }
    res_no_auth = client.post("/api/v1/slots", json=payload)
    assert res_no_auth.status_code == 401

    res_cust = client.post("/api/v1/slots", json=payload, headers=customer_auth_headers)
    assert res_cust.status_code == 403

def test_get_slots_and_businesses_auth_gates(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str],
    business_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    s = Slot(
        owner_id=business_user.id,
        resource_id="auth_slot",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=15,
        status=SlotStatus.AVAILABLE.value
    )
    db.add(s)
    db.commit()

    assert client.get("/api/v1/slots").status_code == 401
    assert client.get(f"/api/v1/slots/{s.id}").status_code == 401
    assert client.get("/api/v1/businesses").status_code == 401

    assert client.get("/api/v1/slots", headers=customer_auth_headers).status_code == 200
    assert client.get(f"/api/v1/slots/{s.id}", headers=customer_auth_headers).status_code == 200
    assert client.get("/api/v1/businesses", headers=customer_auth_headers).status_code == 200

    assert client.get("/api/v1/slots", headers=business_auth_headers).status_code == 200
    assert client.get(f"/api/v1/slots/{s.id}", headers=business_auth_headers).status_code == 200
    assert client.get("/api/v1/businesses", headers=business_auth_headers).status_code == 200

def test_get_businesses_list(
    client: TestClient,
    db: Session,
    business_user: User,
    other_business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    biz1 = Business(
        user_id=business_user.id,
        business_name="Urban Glow Salon",
        category="SALON",
        contact_phone="+919876543210"
    )
    biz2 = Business(
        user_id=other_business_user.id,
        business_name="Apex Math Academy",
        category="TUTOR",
        contact_phone="+919876543211"
    )
    db.add_all([biz1, biz2])
    db.commit()

    res = client.get("/api/v1/businesses", headers=customer_auth_headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    names = [i["business_name"] for i in items]
    assert names == ["Apex Math Academy", "Urban Glow Salon"]
    assert items[0]["category"] == "TUTOR"
    assert items[0]["id"] == biz2.id
    assert items[1]["category"] == "SALON"
    assert items[1]["id"] == biz1.id

def test_slots_response_includes_business_and_category(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    biz = Business(
        user_id=business_user.id,
        business_name="Zen Yoga Studio",
        category="SPORTS",
        contact_phone="+919876543210"
    )
    db.add(biz)
    now = datetime.now(timezone.utc)
    slot = Slot(
        owner_id=business_user.id,
        resource_id="yoga_mat_1",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=3),
        price=20,
        status=SlotStatus.AVAILABLE.value
    )
    db.add(slot)
    db.commit()

    res = client.get("/api/v1/slots", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["business_name"] == "Zen Yoga Studio"
    assert data[0]["category"] == "SPORTS"

    res_single = client.get(f"/api/v1/slots/{slot.id}", headers=customer_auth_headers)
    assert res_single.status_code == 200
    assert res_single.json()["business_name"] == "Zen Yoga Studio"
    assert res_single.json()["category"] == "SPORTS"

def test_slots_filter_by_business_id(
    client: TestClient,
    db: Session,
    business_user: User,
    other_business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    biz1 = Business(user_id=business_user.id, business_name="Clinic A", category="CLINIC", contact_phone="+919876543210")
    biz2 = Business(user_id=other_business_user.id, business_name="Salon B", category="SALON", contact_phone="+919876543211")
    db.add_all([biz1, biz2])
    now = datetime.now(timezone.utc)
    s1 = Slot(owner_id=business_user.id, resource_id="dr_1", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=50)
    s2 = Slot(owner_id=other_business_user.id, resource_id="hair_1", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=30)
    db.add_all([s1, s2])
    db.commit()

    res = client.get(f"/api/v1/slots?business_id={biz1.id}", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == s1.id
    assert data[0]["business_name"] == "Clinic A"

    res2 = client.get(f"/api/v1/slots?business_id={biz2.id}", headers=customer_auth_headers)
    assert res2.status_code == 200
    assert len(res2.json()) == 1
    assert res2.json()[0]["id"] == s2.id

def test_slots_filter_by_category(
    client: TestClient,
    db: Session,
    business_user: User,
    other_business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    biz1 = Business(user_id=business_user.id, business_name="Clinic A", category="CLINIC", contact_phone="+919876543210")
    biz2 = Business(user_id=other_business_user.id, business_name="Salon B", category="SALON", contact_phone="+919876543211")
    db.add_all([biz1, biz2])
    now = datetime.now(timezone.utc)
    s1 = Slot(owner_id=business_user.id, resource_id="dr_1", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=50)
    s2 = Slot(owner_id=other_business_user.id, resource_id="hair_1", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=30)
    db.add_all([s1, s2])
    db.commit()

    res = client.get("/api/v1/slots?category=CLINIC", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == s1.id

    res2 = client.get("/api/v1/slots?category=SALON", headers=customer_auth_headers)
    assert res2.status_code == 200
    assert len(res2.json()) == 1
    assert res2.json()[0]["id"] == s2.id

    res_none = client.get("/api/v1/slots?category=TUTOR", headers=customer_auth_headers)
    assert res_none.status_code == 200
    assert len(res_none.json()) == 0

def test_slots_filter_by_date_range(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    s_tomorrow = Slot(owner_id=business_user.id, resource_id="day1", start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, hours=1), price=20)
    s_day3 = Slot(owner_id=business_user.id, resource_id="day3", start_time=now + timedelta(days=3), end_time=now + timedelta(days=3, hours=1), price=20)
    s_day5 = Slot(owner_id=business_user.id, resource_id="day5", start_time=now + timedelta(days=5), end_time=now + timedelta(days=5, hours=1), price=20)
    db.add_all([s_tomorrow, s_day3, s_day5])
    db.commit()

    date_from = (now + timedelta(days=2)).date().isoformat()
    date_to = (now + timedelta(days=4)).date().isoformat()
    res = client.get(f"/api/v1/slots?date_from={date_from}&date_to={date_to}", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == s_day3.id

    invalid_date_res = client.get("/api/v1/slots?date_from=not-a-date", headers=customer_auth_headers)
    assert invalid_date_res.status_code == 422

def test_slots_filter_by_status(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    s_avail = Slot(owner_id=business_user.id, resource_id="avail", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=20, status=SlotStatus.AVAILABLE.value)
    s_booked = Slot(owner_id=business_user.id, resource_id="booked", start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=3), price=20, status=SlotStatus.BOOKED.value)
    s_held = Slot(owner_id=business_user.id, resource_id="held", start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4), price=20, status=SlotStatus.HELD.value)
    s_cancelled = Slot(owner_id=business_user.id, resource_id="canc", start_time=now + timedelta(hours=4), end_time=now + timedelta(hours=5), price=20, status=SlotStatus.CANCELLED.value)
    db.add_all([s_avail, s_booked, s_held, s_cancelled])
    db.commit()

    res_default = client.get("/api/v1/slots", headers=customer_auth_headers)
    assert res_default.status_code == 200
    ids_default = [s["id"] for s in res_default.json()]
    assert ids_default == [s_avail.id]

    res_booked = client.get("/api/v1/slots?status=BOOKED", headers=customer_auth_headers)
    assert res_booked.status_code == 200
    ids_booked = [s["id"] for s in res_booked.json()]
    assert ids_booked == [s_booked.id]

    res_held = client.get("/api/v1/slots?status=HELD", headers=customer_auth_headers)
    assert res_held.status_code == 200
    ids_held = [s["id"] for s in res_held.json()]
    assert ids_held == [s_held.id]

    res_waitlist = client.get("/api/v1/slots?status=WAITLIST", headers=customer_auth_headers)
    assert res_waitlist.status_code == 200
    ids_waitlist = [s["id"] for s in res_waitlist.json()]
    assert ids_waitlist == [s_booked.id, s_held.id]

    res_all = client.get("/api/v1/slots?status=ALL", headers=customer_auth_headers)
    assert res_all.status_code == 200
    ids_all = [s["id"] for s in res_all.json()]
    assert ids_all == [s_avail.id, s_booked.id, s_held.id]

    res_invalid = client.get("/api/v1/slots?status=INVALID", headers=customer_auth_headers)
    assert res_invalid.status_code == 422

def test_slots_excludes_past_by_default(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    s_past = Slot(owner_id=business_user.id, resource_id="past", start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1), price=20, status=SlotStatus.AVAILABLE.value)
    s_future = Slot(owner_id=business_user.id, resource_id="future", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=20, status=SlotStatus.AVAILABLE.value)
    db.add_all([s_past, s_future])
    db.commit()

    res_default = client.get("/api/v1/slots", headers=customer_auth_headers)
    assert res_default.status_code == 200
    ids = [s["id"] for s in res_default.json()]
    assert s_future.id in ids
    assert s_past.id not in ids

    res_past = client.get("/api/v1/slots?include_past=true", headers=customer_auth_headers)
    assert res_past.status_code == 200
    past_ids = [s["id"] for s in res_past.json()]
    assert s_past.id in past_ids
    assert s_future.id in past_ids

def test_slots_sorted_by_start_time_ascending(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    s3 = Slot(owner_id=business_user.id, resource_id="s3", start_time=now + timedelta(hours=5), end_time=now + timedelta(hours=6), price=20)
    s1 = Slot(owner_id=business_user.id, resource_id="s1", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), price=20)
    s2 = Slot(owner_id=business_user.id, resource_id="s2", start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4), price=20)
    db.add_all([s3, s1, s2])
    db.commit()

    res = client.get("/api/v1/slots", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert [s["id"] for s in data] == [s1.id, s2.id, s3.id]
