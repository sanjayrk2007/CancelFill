import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.config import settings
from app.schemas import (
    ForgotPasswordRequest, MessageResponse, PasswordChange, ResetPasswordRequest, TokenResponse,
    UserLogin, UserRegister, UserResponse, UserUpdate,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PasswordResetToken, User, Business, UserRole
from app.security import create_access_token, hash_password, verify_password
from app.services import notification_service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = User(
        email=user_in.email,
        name=user_in.name,
        password_hash=hash_password(user_in.password),
        role=user_in.role.value,
        phone=user_in.phone
    )
    db.add(user)
    db.flush()
    if user_in.role == UserRole.BUSINESS:
        category_val = user_in.category.value if hasattr(user_in.category, "value") else str(user_in.category)
        business = Business(
            user_id=user.id,
            business_name=user_in.business_name,
            category=category_val,
            contact_phone=user_in.contact_phone,
            contact_address=user_in.contact_address,
        )
        db.add(business)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "")
        password = str(form.get("password") or "")
    else:
        try:
            body = await request.json()
            email = str(body.get("email") or body.get("username") or "")
            password = str(body.get("password") or "")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
@router.patch("/me", response_model=UserResponse)
def update_me(
    update_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    updates = {k: getattr(update_in, k) for k in update_in.model_fields_set}
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")
    if "name" in updates and updates["name"] is None:
        raise HTTPException(status_code=422, detail="name cannot be null")
    for key in ("notify_email", "notify_sms", "notify_push"):
        if key in updates and updates[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null")
    if "phone" in updates:
        updates["phone"] = updates["phone"] or None

    biz_fields = {"business_name", "category", "contact_phone", "contact_address"}
    biz_updates = {k: updates.pop(k) for k in biz_fields if k in updates}
    if biz_updates:
        if current_user.role != UserRole.BUSINESS.value:
            raise HTTPException(status_code=403, detail="Only business accounts can update business profile fields")
        for key in ("business_name", "category", "contact_phone"):
            if key in biz_updates and biz_updates[key] is None:
                raise HTTPException(status_code=422, detail=f"{key} cannot be null")
        if current_user.business_profile is None:
            current_user.business_profile = Business(
                user_id=current_user.id,
                business_name=biz_updates.get("business_name") or current_user.name,
                category=biz_updates.get("category").value if hasattr(biz_updates.get("category"), "value") else (biz_updates.get("category") or "OTHER"),
                contact_phone=biz_updates.get("contact_phone") or (current_user.phone or ""),
                contact_address=biz_updates.get("contact_address")
            )
            db.add(current_user.business_profile)
        else:
            for k, v in biz_updates.items():
                if k == "category" and hasattr(v, "value"):
                    v = v.value
                setattr(current_user.business_profile, k, v)
        if "contact_phone" in biz_updates and "phone" not in updates and not current_user.phone:
            current_user.phone = biz_updates["contact_phone"]

    for key, value in updates.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    pw_in: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    if not verify_password(pw_in.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.password_hash = hash_password(pw_in.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """Always answers the same way so the endpoint cannot be used to discover registered emails."""
    generic = MessageResponse(message="If that email is registered, a reset link has been sent.")
    user = db.query(User).filter(User.email == body.email.strip()).first()
    if user is None:
        return generic
    now = datetime.now(timezone.utc)
    for old in db.scalars(select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))).all():
        old.used_at = now  # only the newest link works
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=_hash_token(token), created_at=now,
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    ))
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    notification_service.notify_password_reset(db, user.id, link, now=now)
    db.commit()
    return generic


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    now = datetime.now(timezone.utc)
    record = db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == _hash_token(body.token)).with_for_update()).first()
    expires = record.expires_at if record and record.expires_at.tzinfo else (
        record.expires_at.replace(tzinfo=timezone.utc) if record else None)
    if record is None or record.used_at is not None or expires <= now:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user.password_hash = hash_password(body.new_password)
    record.used_at = now
    db.commit()
    return MessageResponse(message="Password updated. You can now sign in.")
