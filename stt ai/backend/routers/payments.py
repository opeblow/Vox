from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.payment import PaymentInit, PaymentResponse
from backend.services.paystack import (
    initialize_transaction,
    verify_transaction,
    handle_webhook,
    verify_webhook_signature,
)

router = APIRouter(tags=["Payments"])


@router.post(
    "/initialize",
    response_model=PaymentResponse,
    dependencies=[Depends(get_current_user)],
)
def initialize_payment(payment: PaymentInit, db: Session = Depends(get_db)):
    result = initialize_transaction(payment.email, payment.amount, payment.callback_url)
    return PaymentResponse(status="success", message="Payment initialized", data=result)


@router.post(
    "/webhook",
    response_model=PaymentResponse,
)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("x-paystack-signature")
    if not sig_header:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    if not verify_webhook_signature(payload, sig_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    event = json.loads(payload)
    result = handle_webhook(event["event"], event["data"], db)
    return PaymentResponse(status="success", message="Webhook processed", data=result)


@router.get(
    "/verify/{reference}",
    response_model=PaymentResponse,
)
def verify_payment(reference: str, db: Session = Depends(get_db)):
    result = verify_transaction(reference)
    return PaymentResponse(status="success", message="Payment verified", data=result)
