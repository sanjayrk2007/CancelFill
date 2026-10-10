import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Hold, HoldStatus, Slot, SlotStatus
from app.services.allocation_service import cancel_past_slot, expire_hold

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    BackgroundScheduler = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
scheduler: Optional["BackgroundScheduler"] = None


def expire_due_holds(now: Optional[datetime] = None) -> int:
    """Expire all due active holds, using one transaction/session per hold."""
    current_time = now or datetime.now(timezone.utc)
    finder_db = SessionLocal()
    try:
        hold_ids = list(
            finder_db.scalars(
                select(Hold.id).where(
                    Hold.status == HoldStatus.ACTIVE.value,
                    Hold.expires_at <= current_time,
                )
            ).all()
        )
    finally:
        finder_db.close()

    expired_count = 0
    for hold_id in hold_ids:
        db = SessionLocal()
        try:
            expire_hold(db=db, hold_id=hold_id, now=current_time)
            expired_count += 1
        except Exception:
            logger.exception("failed_to_expire_hold hold_id=%s", hold_id)
        finally:
            db.close()
    return expired_count


def cancel_past_slots(now: Optional[datetime] = None) -> int:
    """Cancel AVAILABLE/HELD slots whose start time has passed."""
    current_time = now or datetime.now(timezone.utc)
    finder_db = SessionLocal()
    try:
        slot_ids = list(
            finder_db.scalars(
                select(Slot.id).where(
                    Slot.start_time <= current_time,
                    Slot.status.in_([SlotStatus.AVAILABLE.value, SlotStatus.HELD.value]),
                )
            ).all()
        )
    finally:
        finder_db.close()

    cancelled = 0
    for slot_id in slot_ids:
        db = SessionLocal()
        try:
            if cancel_past_slot(db=db, slot_id=slot_id, now=current_time):
                cancelled += 1
        except Exception:
            logger.exception("failed_to_cancel_past_slot slot_id=%s", slot_id)
        finally:
            db.close()
    return cancelled


def start_scheduler() -> None:
    global scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("scheduler_disabled")
        return
    if BackgroundScheduler is None:
        logger.warning("scheduler_unavailable apscheduler_not_installed")
        return
    if scheduler and scheduler.running:
        return
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        expire_due_holds,
        "interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="expire_due_holds",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        cancel_past_slots,
        "interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="cancel_past_slots",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("scheduler_started interval_seconds=%s", settings.SCHEDULER_INTERVAL_SECONDS)


def stop_scheduler() -> None:
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
    scheduler = None