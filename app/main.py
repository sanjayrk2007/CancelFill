from fastapi import FastAPI
from app.config import settings
from app.database import Base, engine
from app.routes import slots, waitlist, bookings, cancellations, holds

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

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
        {"name": "Slots", "description": "Manage resource slots"},
        {"name": "Waitlist", "description": "Register customers and view prioritized waitlists"},
        {"name": "Bookings", "description": "Create and view initial bookings for demonstration"},
        {"name": "Cancellations", "description": "Cancel bookings and trigger recovery workflow"},
        {"name": "Holds", "description": "Inspect holds and evaluate timestamp expiry"},
    ]
)

# Register router endpoints under API_V1_STR prefix
app.include_router(slots.router, prefix=settings.API_V1_STR)
app.include_router(waitlist.router, prefix=settings.API_V1_STR)
app.include_router(bookings.router, prefix=settings.API_V1_STR)
app.include_router(cancellations.router, prefix=settings.API_V1_STR)
app.include_router(holds.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs",
        "review_stage": "Review-1"
    }
