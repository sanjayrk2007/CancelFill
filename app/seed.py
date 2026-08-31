from datetime import datetime, timedelta, timezone
from app.database import SessionLocal, Base, engine
from app.models import Slot, SlotStatus, WaitlistEntry, WaitlistStatus, Booking, BookingStatus, Hold

def seed_database():
    """
    Populates a small, deterministic seed dataset for Review-1 demonstration.
    
    Dataset contents:
    - 2 Slots:
        * Slot 1: Booked by Charlie (has 2 waitlist entries)
        * Slot 2: Available
    - 2 Waitlist entries for Slot 1:
        * Customer A (Alice): Joined earlier (10:00 AM UTC) -> Highest Priority
        * Customer B (Bob): Joined later (10:05 AM UTC) -> Second Priority
    - 1 Active Booking for Slot 1 (Charlie) ready to be cancelled during the demo.
    """
    # Recreate tables for clean seed state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Create Slots
        slot1 = Slot(
            id="slot-demo-1",
            resource_id="Dr_Smith_Consultation_10AM",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            status=SlotStatus.BOOKED.value
        )

        slot2 = Slot(
            id="slot-demo-2",
            resource_id="Dr_Smith_Consultation_11AM",
            start_time=now + timedelta(hours=3),
            end_time=now + timedelta(hours=4),
            status=SlotStatus.AVAILABLE.value
        )

        db.add_all([slot1, slot2])
        db.commit()

        # 2. Create Active Booking on Slot 1
        booking1 = Booking(
            id="booking-demo-1",
            slot_id=slot1.id,
            user_id="user_charlie",
            booked_at=now - timedelta(hours=1),
            status=BookingStatus.CONFIRMED.value
        )
        db.add(booking1)
        db.commit()

        # 3. Create Waitlist Entries for Slot 1 with clear timestamp ordering
        # Customer A (Alice) joined 30 mins ago
        waitlist_a = WaitlistEntry(
            id="waitlist-a",
            slot_id=slot1.id,
            user_id="customer_a_alice",
            joined_at=now - timedelta(minutes=30),
            status=WaitlistStatus.WAITING.value
        )
        # Customer B (Bob) joined 15 mins ago
        waitlist_b = WaitlistEntry(
            id="waitlist-b",
            slot_id=slot1.id,
            user_id="customer_b_bob",
            joined_at=now - timedelta(minutes=15),
            status=WaitlistStatus.WAITING.value
        )

        db.add_all([waitlist_a, waitlist_b])
        db.commit()

        print("=" * 60)
        print("SEED DATA SUCCESSFULLY POPULATED FOR REVIEW-1 DEMO")
        print("=" * 60)
        print(f"Slot 1 ID (Booked):         {slot1.id}")
        print(f"Booking ID (to Cancel):    {booking1.id} (User: {booking1.user_id})")
        print(f"Waitlist Customer A:       {waitlist_a.user_id} (Joined 30m ago)")
        print(f"Waitlist Customer B:       {waitlist_b.user_id} (Joined 15m ago)")
        print(f"Slot 2 ID (Available):      {slot2.id}")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
