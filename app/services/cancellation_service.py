from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Booking, User
from app.services.allocation_service import cancel_booking

def process_cancellation(db: Session, booking_id: str, actor: Optional[User | str] = None) -> Dict[str, Any]:
    if actor is None:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        actor = booking.user_id if booking else ""
    return cancel_booking(db=db, booking_id=booking_id, actor=actor)
