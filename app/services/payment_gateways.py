"""Payment gateway adapters.

`razorpay` talks to the real API. `mock` implements the same order/signature/refund contract
locally (no network) for development, demos and tests. `none` disables payments entirely, in
which case bookings behave exactly as before.
"""
import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.models import Slot


class GatewayError(Exception):
    pass


def to_minor_units(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).to_integral_value())


def _hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class BaseGateway:
    name = "base"
    key_id = ""
    _signing_secret = ""
    _webhook_secret = ""

    def create_order(self, amount_minor: int, currency: str, receipt: str) -> str:
        raise NotImplementedError

    def refund(self, provider_payment_id: str, amount_minor: int, reason: str) -> str:
        raise NotImplementedError

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        if not self._signing_secret or not signature:
            return False
        expected = _hmac(self._signing_secret, f"{order_id}|{payment_id}".encode("utf-8"))
        return hmac.compare_digest(expected, signature)

    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not self._webhook_secret or not signature:
            return False
        return hmac.compare_digest(_hmac(self._webhook_secret, raw_body), signature)


class RazorpayGateway(BaseGateway):
    name = "razorpay"
    base_url = "https://api.razorpay.com/v1"

    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self._signing_secret = settings.RAZORPAY_KEY_SECRET
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    def _post(self, path: str, payload: dict) -> dict:
        try:
            resp = httpx.post(
                f"{self.base_url}{path}", json=payload,
                auth=(self.key_id, self._signing_secret), timeout=20,
            )
        except httpx.HTTPError as exc:
            raise GatewayError(f"razorpay request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise GatewayError(f"razorpay error {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def create_order(self, amount_minor: int, currency: str, receipt: str) -> str:
        data = self._post("/orders", {
            "amount": amount_minor, "currency": currency, "receipt": receipt[:40], "payment_capture": 1,
        })
        return data["id"]

    def refund(self, provider_payment_id: str, amount_minor: int, reason: str) -> str:
        data = self._post(f"/payments/{provider_payment_id}/refund", {
            "amount": amount_minor, "notes": {"reason": reason[:250]},
        })
        return data["id"]


class MockGateway(BaseGateway):
    name = "mock"
    key_id = "mock_key"

    def __init__(self) -> None:
        self._signing_secret = settings.MOCK_PAYMENT_SECRET
        self._webhook_secret = settings.MOCK_PAYMENT_SECRET

    def create_order(self, amount_minor: int, currency: str, receipt: str) -> str:
        return f"order_mock_{uuid.uuid4().hex[:16]}"

    def refund(self, provider_payment_id: str, amount_minor: int, reason: str) -> str:
        return f"rfnd_mock_{uuid.uuid4().hex[:16]}"

    def simulate_payment(self, order_id: str) -> dict:
        payment_id = f"pay_mock_{uuid.uuid4().hex[:16]}"
        signature = _hmac(self._signing_secret, f"{order_id}|{payment_id}".encode("utf-8"))
        return {"provider_order_id": order_id, "provider_payment_id": payment_id, "signature": signature}


def get_gateway() -> Optional[BaseGateway]:
    provider = settings.PAYMENT_PROVIDER.lower()
    if provider == "razorpay":
        if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
            raise GatewayError("PAYMENT_PROVIDER=razorpay but RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set")
        return RazorpayGateway()
    if provider == "mock":
        return MockGateway()
    return None


def payment_required(slot: Slot) -> bool:
    """True when this slot must be paid for before a booking can be confirmed."""
    return settings.PAYMENT_PROVIDER.lower() in ("mock", "razorpay") and Decimal(slot.price or 0) > 0
