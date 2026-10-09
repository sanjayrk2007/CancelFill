from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.schemas import PasswordChange, TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.security import create_access_token, hash_password, verify_password

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
        role=user_in.role.value
    )
    db.add(user)
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
    current_user.name = update_in.name
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
