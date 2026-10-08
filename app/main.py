import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base, engine, get_db
from app.routes import slots, waitlist, bookings, cancellations, holds, auth, me, business
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
### CancelFill – Intelligent Cancellation Recovery & Waitlist Platform
**Software Engineering Review-1 Backend Prototype**

This API demonstrates the four completed Review-1 modules:
1. **Database Schema**: PostgreSQL schema managing `slots`, `waitlist_entries`, `holds`, and `bookings`.
2. **Core FastAPI Scaffold**: Slot creation, viewing endpoints, and waitlist registration.
3. **First-Pass Cancellation & Candidate Selection**: Booking cancellation releases slot, evaluates waitlist ordered by `joined_at ASC`, selects earliest eligible candidate, and creates a temporary hold.
4. **Basic Timestamp-based Hold Expiry**: Pure timestamp check evaluating `current_time > expires_at`.
    """,
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and user management"},
        {"name": "Slots", "description": "Manage resource slots"},
        {"name": "Waitlist", "description": "Register customers and view prioritized waitlists"},
        {"name": "Bookings", "description": "Create and view initial bookings for demonstration"},
        {"name": "Cancellations", "description": "Cancel bookings and trigger recovery workflow"},
        {"name": "Holds", "description": "Inspect holds and evaluate timestamp expiry"},
    ],
    lifespan=lifespan
)

cors_origins: list[str] = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(slots.router, prefix=settings.API_V1_STR)
app.include_router(waitlist.router, prefix=settings.API_V1_STR)
app.include_router(bookings.router, prefix=settings.API_V1_STR)
app.include_router(cancellations.router, prefix=settings.API_V1_STR)
app.include_router(holds.router, prefix=settings.API_V1_STR)
app.include_router(me.router, prefix=settings.API_V1_STR)
app.include_router(business.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["System"])
def root() -> Dict[str, str]:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs",
        "review_stage": "Review-1"
    }

@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unreachable"
        )
