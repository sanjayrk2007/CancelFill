from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Business, User
from app.schemas import BusinessListItem

router = APIRouter(prefix="/businesses", tags=["Businesses"])

@router.get("", response_model=List[BusinessListItem], summary="List businesses for filter dropdown")
def list_businesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Business]:
    return db.query(Business).order_by(Business.business_name.asc(), Business.id.asc()).all()
