from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.database import SessionLocal, Base, engine
from app.models import Slot, SlotStatus, WaitlistEntry, WaitlistStatus, Booking, BookingStatus, User, UserRole
from app.security import hash_password

def seed_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pwd_hash = hash_password("password123")

        biz_user = User(
            id="user-biz-1",
            email="dr_smith@example.com",
            name="Dr. Smith",
            password_hash=pwd_hash,
            role=UserRole.BUSINESS.value,
            created_at=now - timedelta(days=1)
        )
        cust_alice = User(
            id="user-cust-alice",
            email="alice@example.com",
            name="Alice",
            password_hash=pwd_hash,
            role=UserRole.CUSTOMER.value,
            created_at=now - timedelta(days=1)
        )
        cust_bob = User(
            id="user-cust-bob",
            email="bob@example.com",
            name="Bob",
            password_hash=pwd_hash,
            role=UserRole.CUSTOMER.value,
            created_at=now - timedelta(days=1)
        )
        cust_charlie = User(
            id="user-cust-charlie",
            email="charlie@example.com",
            name="Charlie",
            password_hash=pwd_hash,
            role=UserRole.CUSTOMER.value,
            created_at=now - timedelta(days=1)
        )

        db.add_all([biz_user, cust_alice, cust_bob, cust_charlie])
        db.commit()

        slot1 = Slot(
            id="slot-demo-1",
            owner_id=biz_user.id,
            resource_id="Dr_Smith_Consultation_10AM",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            price=Decimal("50.00"),
            status=SlotStatus.BOOKED.value
        )

        slot2 = Slot(
            id="slot-demo-2",
            owner_id=biz_user.id,
            resource_id="Dr_Smith_Consultation_11AM",
            start_time=now + timedelta(hours=3),
            end_time=now + timedelta(hours=4),
            price=Decimal("75.00"),
            status=SlotStatus.AVAILABLE.value
        )

        db.add_all([slot1, slot2])
        db.commit()

        booking1 = Booking(
            id="booking-demo-1",
            slot_id=slot1.id,
            user_id=cust_charlie.id,
            booked_at=now - timedelta(hours=1),
            status=BookingStatus.CONFIRMED.value
        )
        db.add(booking1)
        db.commit()

        waitlist_a = WaitlistEntry(
            id="waitlist-a",
            slot_id=slot1.id,
            user_id=cust_alice.id,
            joined_at=now - timedelta(minutes=30),
            status=WaitlistStatus.WAITING.value
        )
        waitlist_b = WaitlistEntry(
            id="waitlist-b",
            slot_id=slot1.id,
            user_id=cust_bob.id,
            joined_at=now - timedelta(minutes=15),
            status=WaitlistStatus.WAITING.value
        )

        db.add_all([waitlist_a, waitlist_b])
        db.commit()

        print("=" * 60)
        print("SEED DATA SUCCESSFULLY POPULATED FOR REVIEW-1 DEMO")
        print("=" * 60)
        print(f"Business User:             {biz_user.email} (ID: {biz_user.id})")
        print(f"Customer Alice:            {cust_alice.email} (ID: {cust_alice.id})")
        print(f"Customer Bob:              {cust_bob.email} (ID: {cust_bob.id})")
        print(f"Customer Charlie:          {cust_charlie.email} (ID: {cust_charlie.id})")
        print(f"Slot 1 ID (Booked):         {slot1.id}")
        print(f"Booking ID (to Cancel):    {booking1.id} (User: {booking1.user_id})")
        print(f"Slot 2 ID (Available):      {slot2.id}")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
