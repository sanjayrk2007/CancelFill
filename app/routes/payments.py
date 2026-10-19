from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_customer
from app.models import Payment, User
from app.schemas import (
    BookingResponse, CheckoutRequest, CheckoutResponse, ConfirmPaymentRequest, MockPaymentResponse,
    PaymentConfigResponse, PaymentResponse,
)
from app.services import payment_service
from app.services.allocation_service import AlreadyHolding
from app.services.payment_gateways import GatewayError, get_gateway
from app.services.payment_service import PaymentError, PaymentNotRequired
from app.services.state_machine import InvalidTransition, NotFoundError, OfferExpired

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/config", response_model=PaymentConfigResponse, summary="Payment provider info for the frontend")
def payment_config() -> PaymentConfigResponse:
    try:
        gateway = get_gateway()
    except GatewayError:
        gateway = None
    return PaymentConfigResponse(
        enabled=gateway is not None,
        provider=gateway.name if gateway else "none",
        key_id=gateway.key_id if gateway else None,
        currency=settings.PAYMENT_CURRENCY,
    )


@router.post("/checkout", response_model=CheckoutResponse, summary="Start paying for a slot or a waitlist offer")
def checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> dict:
    try:
        return payment_service.start_checkout(db, current_user.id, slot_id=body.slot_id, hold_id=body.hold_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OfferExpired, InvalidTransition):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This offer is no longer available")
    except (PaymentNotRequired, AlreadyHolding, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except GatewayError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider is unavailable. Try again.")


@router.post("/confirm", response_model=BookingResponse, summary="Verify a completed payment and confirm the booking")
def confirm(
    body: ConfirmPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> BookingResponse:
    try:
        booking = payment_service.confirm_payment(
            db, body.payment_id, current_user.id, body.provider_order_id, body.provider_payment_id, body.signature
        )
        return BookingResponse.model_validate(booking)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OfferExpired as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PaymentNotRequired as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{payment_id}/mock-pay", response_model=MockPaymentResponse,
             summary="Simulate the customer paying (PAYMENT_PROVIDER=mock only)")
def mock_pay(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> dict:
    try:
        return payment_service.simulate_mock_payment(db, payment_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PaymentNotRequired as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/webhook", summary="Gateway webhook (signature verified)")
async def webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    try:
        result = payment_service.handle_webhook(db, raw, x_razorpay_signature)
    except PaymentError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
    except PaymentNotRequired:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payments are not enabled")
    return {"status": "ok", "result": result}


@router.get("", response_model=List[PaymentResponse], summary="My payments")
def my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> List[Payment]:
    return list(db.scalars(
        select(Payment).where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc(), Payment.id.asc())
    ).all())
