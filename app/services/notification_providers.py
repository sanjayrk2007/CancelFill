"""Outbound channel adapters (email, SMS, web push).

Each sender raises on failure. `PermanentDeliveryError` means retrying cannot help
(e.g. an expired push subscription). When a channel is not configured, the message is
logged instead so local development works without any credentials.
"""
import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Callable, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PermanentDeliveryError(Exception):
    pass


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("[console-email] to=%s subject=%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


def send_sms(to: str, body: str) -> None:
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
        logger.info("[console-sms] to=%s body=%s", to, body)
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    resp = httpx.post(
        url,
        data={"To": to, "From": settings.TWILIO_FROM_NUMBER, "Body": body[:1500]},
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        timeout=15,
    )
    if resp.status_code in (400, 404):
        # Invalid or unreachable destination number: retrying will not fix it.
        raise PermanentDeliveryError(f"twilio rejected message: {resp.text[:200]}")
    resp.raise_for_status()


def send_push(subscription: Dict[str, object], title: str, body: str, url: str | None) -> None:
    if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY):
        logger.info("[console-push] title=%s body=%s", title, body)
        return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError as exc:  # pragma: no cover - declared in requirements.txt
        raise RuntimeError("pywebpush is not installed") from exc
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body, "url": url or "/"}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            timeout=15,
        )
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            raise PermanentDeliveryError("push subscription is gone") from exc
        raise


# Looked up at call time so tests can swap in fakes.
senders: Dict[str, Callable[..., None]] = {
    "EMAIL": send_email,
    "SMS": send_sms,
    "PUSH": send_push,
}
