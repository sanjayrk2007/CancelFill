from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_customer
from app.models import User, WaitlistEntry
from app.schemas import WaitlistCreate, WaitlistResponse
from app.services.allocation_service import join_waitlist, leave_waitlist
from app.services.state_machine import NotFoundError, InvalidTransition

router = APIRouter(tags=["Waitlist"])

@router.post("/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED, summary="Register customer on waitlist")
def add_to_waitlist(
    entry_in: WaitlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> WaitlistEntry:
    try:
        return join_waitlist(
            db=db,
            slot_id=entry_in.slot_id,
            user_id=current_user.id,
            joined_at=entry_in.joined_at
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.delete("/waitlist/{waitlist_id}", response_model=WaitlistResponse, status_code=status.HTTP_200_OK, summary="Cancel waitlist entry")
def cancel_waitlist_entry(
    waitlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
) -> WaitlistEntry:
    try:
        return leave_waitlist(db=db, waitlist_id=waitlist_id, actor=current_user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
