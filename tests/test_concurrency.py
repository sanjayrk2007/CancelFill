import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Callable, List

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Booking,
    BookingSource,
    BookingStatus,
    Hold,
    HoldStatus,
    Slot,
    SlotStatus,
    User,
    UserRole,
    WaitlistEntry,
    WaitlistStatus,
)
from app.security import hash_password
from app.services.allocation_service import accept_hold, book_slot, cancel_booking, expire_hold
from app.services.state_machine import InvalidTransition, OfferExpired
from tests.conftest import TestingSessionLocal
from tests.invariants import assert_invariants


def _is_postgres_test_database() -> bool:
    return (os.getenv("TEST_DATABASE_URL") or "").startswith(("postgresql://", "postgresql+"))


pytestmark = [
    pytest.mark.concurrency,
    pytest.mark.skipif(
        not _is_postgres_test_database(),
        reason="concurrency tests require TEST_DATABASE_URL to point at PostgreSQL",
    ),
]


CONFLICT_EXCEPTIONS = (InvalidTransition, OfferExpired, ValueError, IntegrityError)


def _run_simultaneously(n: int, task: Callable[[Session], int]) -> List[int]:
    barrier = threading.Barrier(n)

    def worker() -> int:
        db = TestingSessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                return task(db)
            except CONFLICT_EXCEPTIONS:
                db.rollback()
                return 409
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=n) as executor:
        return list(executor.map(lambda _: worker(), range(n)))


def _user(db: Session, email: str, role: UserRole = UserRole.CUSTOMER) -> User:
    user = User(
        email=email,
        name=email.split("@")[0],
        password_hash=hash_password("password123"),
        role=role.value,
    )
    db.add(user)
    db.flush()
    return user


def _slot(db: Session, owner: User, resource_id: str, status: SlotStatus = SlotStatus.AVAILABLE) -> Slot:
    now = datetime.now(timezone.utc)
    slot = Slot(
        owner_id=owner.id,
        resource_id=resource_id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price="50.00",
        status=status.value,
    )
    db.add(slot)
    db.flush()
    return slot


@pytest.mark.parametrize("repeat", range(5))
def test_concurrent_accept_same_hold_same_user_has_exactly_one_success(db: Session, repeat: int) -> None:
    now = datetime.now(timezone.utc)
    business = _user(db, f"accept-biz-{repeat}@example.com", UserRole.BUSINESS)
    customer = _user(db, f"accept-customer-{repeat}@example.com")
    cancelled_customer = _user(db, f"accept-cancelled-{repeat}@example.com")
    slot = _slot(db, business, f"accept-{repeat}", SlotStatus.HELD)
    cancelled_booking = Booking(
        slot_id=slot.id,
        user_id=cancelled_customer.id,
        booked_at=now - timedelta(minutes=1),
        status=BookingStatus.CANCELLED.value,
        source=BookingSource.DIRECT.value,
    )
    entry = WaitlistEntry(slot_id=slot.id, user_id=customer.id, status=WaitlistStatus.OFFERED.value)
    hold = Hold(
        slot_id=slot.id,
        user_id=customer.id,
        expires_at=now + timedelta(minutes=15),
        status=HoldStatus.ACTIVE.value,
    )
    db.add_all([cancelled_booking, entry, hold])
    db.commit()

    results = _run_simultaneously(10, lambda session: 200 if accept_hold(session, hold.id, customer.id) else 409)

    assert results.count(200) == 1
    assert results.count(409) == 9
    assert db.query(Booking).filter(Booking.slot_id == slot.id, Booking.status == BookingStatus.CONFIRMED.value).count() == 1
    assert_invariants(db)


@pytest.mark.parametrize("repeat", range(5))
def test_concurrent_direct_booking_one_available_slot_has_exactly_one_booking(db: Session, repeat: int) -> None:
    business = _user(db, f"book-biz-{repeat}@example.com", UserRole.BUSINESS)
    customers = [_user(db, f"book-customer-{repeat}-{i}@example.com") for i in range(20)]
    slot = _slot(db, business, f"book-{repeat}")
    db.commit()

    barrier = threading.Barrier(20)

    def worker(user_id: str) -> int:
        session = TestingSessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                book_slot(session, slot.id, user_id)
                return 201
            except CONFLICT_EXCEPTIONS:
                session.rollback()
                return 409
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(worker, [customer.id for customer in customers]))

    assert results.count(201) == 1
    assert db.query(Booking).filter(Booking.slot_id == slot.id, Booking.status == BookingStatus.CONFIRMED.value).count() == 1
    assert_invariants(db)


@pytest.mark.parametrize("repeat", range(5))
def test_concurrent_cancel_same_booking_one_success_one_hold_created(db: Session, repeat: int) -> None:
    now = datetime.now(timezone.utc)
    business = _user(db, f"cancel-biz-{repeat}@example.com", UserRole.BUSINESS)
    customer = _user(db, f"cancel-customer-{repeat}@example.com")
    waiting = _user(db, f"cancel-waiting-{repeat}@example.com")
    slot = _slot(db, business, f"cancel-{repeat}", SlotStatus.BOOKED)
    booking = Booking(
        slot_id=slot.id,
        user_id=customer.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value,
    )
    waitlist_entry = WaitlistEntry(slot_id=slot.id, user_id=waiting.id, joined_at=now, status=WaitlistStatus.WAITING.value)
    db.add_all([booking, waitlist_entry])
    db.commit()

    results = _run_simultaneously(2, lambda session: 200 if cancel_booking(session, booking.id, customer.id)["booking_status"] == BookingStatus.CANCELLED.value else 409)

    assert results.count(200) == 1
    assert results.count(409) == 1
    assert db.query(Hold).filter(Hold.slot_id == slot.id, Hold.status == HoldStatus.ACTIVE.value).count() == 1
    assert_invariants(db)


@pytest.mark.parametrize("repeat", range(5))
def test_concurrent_accept_and_expire_overdue_hold_ends_consistently(db: Session, repeat: int) -> None:
    now = datetime.now(timezone.utc)
    business = _user(db, f"race-biz-{repeat}@example.com", UserRole.BUSINESS)
    first = _user(db, f"race-first-{repeat}@example.com")
    second = _user(db, f"race-second-{repeat}@example.com")
    original = _user(db, f"race-original-{repeat}@example.com")
    slot = _slot(db, business, f"race-{repeat}", SlotStatus.HELD)
    cancelled_booking = Booking(
        slot_id=slot.id,
        user_id=original.id,
        booked_at=now - timedelta(hours=1),
        status=BookingStatus.CANCELLED.value,
        source=BookingSource.DIRECT.value,
    )
    first_entry = WaitlistEntry(slot_id=slot.id, user_id=first.id, joined_at=now - timedelta(minutes=10), status=WaitlistStatus.OFFERED.value)
    second_entry = WaitlistEntry(slot_id=slot.id, user_id=second.id, joined_at=now - timedelta(minutes=5), status=WaitlistStatus.WAITING.value)
    hold = Hold(
        slot_id=slot.id,
        user_id=first.id,
        expires_at=now - timedelta(seconds=1),
        status=HoldStatus.ACTIVE.value,
    )
    db.add_all([cancelled_booking, first_entry, second_entry, hold])
    db.commit()

    barrier = threading.Barrier(2)

    def accept_worker() -> int:
        session = TestingSessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                accept_hold(session, hold.id, first.id)
                return 200
            except CONFLICT_EXCEPTIONS:
                session.rollback()
                return 409
        finally:
            session.close()

    def expire_worker() -> int:
        session = TestingSessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                expire_hold(session, hold.id)
                return 200
            except CONFLICT_EXCEPTIONS:
                session.rollback()
                return 409
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(accept_worker), executor.submit(expire_worker)]
        [future.result() for future in results]

    db.expire_all()
    refreshed_slot = db.query(Slot).filter(Slot.id == slot.id).one()
    confirmed = db.query(Booking).filter(Booking.slot_id == slot.id, Booking.status == BookingStatus.CONFIRMED.value).all()
    active_holds = db.query(Hold).filter(Hold.slot_id == slot.id, Hold.status == HoldStatus.ACTIVE.value).all()
    expired_original = db.query(Hold).filter(Hold.id == hold.id, Hold.status == HoldStatus.EXPIRED.value).first()

    if confirmed:
        assert len(confirmed) == 1
        assert refreshed_slot.status == SlotStatus.BOOKED.value
    else:
        assert expired_original is not None
        assert len(active_holds) == 1
        assert active_holds[0].user_id == second.id
        assert refreshed_slot.status == SlotStatus.HELD.value
    assert_invariants(db)