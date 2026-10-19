from datetime import timezone,datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_business
from app.models import Slot, User
from app.schemas import SlotCreate, SlotResponse, SlotUpdate
from app.services.slot_service import remove_slot, update_slot
from app.services.state_machine import NotFoundError

router = APIRouter(prefix="/slots", tags=["Slots"])

@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED, summary="Create a new time slot")
def create_slot(
    slot_in: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business)
) -> Slot:
    if slot_in.start_time.tzinfo is None:
        slot_in.start_time = slot_in.start_time.replace(tzinfo=timezone.utc)
    if slot_in.end_time.tzinfo is None:
        slot_in.end_time = slot_in.end_time.replace(tzinfo=timezone.utc)

    if slot_in.end_time <= slot_in.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be greater than start_time"
        )

    if slot_in.start_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must be in the future"
        )

    slot = Slot(
        owner_id=current_user.id,
        resource_id=slot_in.resource_id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        price=slot_in.price,
        capacity=slot_in.capacity
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot
@router.get("", response_model=List[SlotResponse], summary="List all slots")
def list_slots(db: Session = Depends(get_db)) -> List[Slot]:
    return db.query(Slot).order_by(Slot.start_time.asc(), Slot.id.asc()).all()

@router.get("/{slot_id}", response_model=SlotResponse, summary="Get slot by ID")
def get_slot(slot_id: str, db: Session = Depends(get_db)) -> Slot:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
    return slot


@router.patch("/{slot_id}", response_model=SlotResponse, summary="Edit an unbooked slot (FR-07)")
def edit_slot(
    slot_id: str,
    slot_in: SlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> Slot:
    changes = {k: getattr(slot_in, k) for k in slot_in.model_fields_set}
    for key in ("resource_id", "start_time", "end_time", "price", "capacity"):
        if key in changes and changes[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null")
    try:
        slot = update_slot(db=db, slot_id=slot_id, owner_id=current_user.id, changes=changes)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return slot


@router.delete("/{slot_id}", response_model=SlotResponse, summary="Remove an unbooked slot (FR-08)")
def delete_slot(
    slot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
) -> Slot:
    try:
        return remove_slot(db=db, slot_id=slot_id, owner_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
