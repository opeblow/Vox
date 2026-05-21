import hashlib
import hmac
import httpx
from backend.config import settings
from backend.models.user import User
from backend.models.payment import Payment
from sqlalchemy.orm import Session

PAYSTACK_BASE = "https://api.paystack.co"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(email: str, amount: int, callback_url: str | None = None) -> dict:
    payload = {
        "email": email,
        "amount": amount,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    resp = httpx.post(
        f"{PAYSTACK_BASE}/transaction/initialize",
        json=payload,
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json()

    return {
        "authorization_url": data["data"]["authorization_url"],
        "reference": data["data"]["reference"],
    }


def verify_transaction(reference: str) -> dict:
    resp = httpx.get(
        f"{PAYSTACK_BASE}/transaction/verify/{reference}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


def handle_webhook(event: str, data: dict, db: Session) -> dict:
    from fastapi import HTTPException, status

    if event == "charge.success":
        paystack_ref = data.get("reference")
        if not paystack_ref:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing reference")

        customer_email = data.get("customer", {}).get("email")
        if not customer_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing customer email")

        user = db.query(User).filter(User.email == customer_email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.plan = "premium"
        db.add(user)

        payment = Payment(
            user_id=user.id,
            paystack_ref=paystack_ref,
            amount=data.get("amount", 0),
            currency=data.get("currency", "NGN"),
            status="success",
        )
        db.add(payment)
        db.commit()

        return {"status": "success", "message": "Payment processed and user upgraded to premium"}

    return {"status": "ignored", "message": f"Event {event} not handled"}


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        payload,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
