from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import httpx
import uuid
import hmac
import hashlib
import json
from app.database import get_db
from app.models.order import Order, OrderStatus
from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])

from pydantic import BaseModel, EmailStr, Field

class PaymentInitializeRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="The unique UUID of the order to initialize payment for.")

class PaymentInitializeResponse(BaseModel):
    authorization_url: str = Field(..., description="The Paystack URL to redirect the user to for payment.")
    reference: str = Field(..., description="The unique transaction reference generated for this payment.")
    access_code: str = Field(..., description="The Paystack access code for the transaction.")

@router.post(
    "/initialize", 
    response_model=PaymentInitializeResponse,
    summary="Initialize Paystack Transaction",
    description="Creates a new transaction on Paystack and returns the authorization URL for user redirection."
)
async def initialize_payment(
    payload: PaymentInitializeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch order
    result = await db.execute(select(Order).where(Order.id == payload.order_id, Order.buyer_id == current_user.id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=400, detail="Order is not in pending state")

    # 2. Prepare Paystack request
    # Paystack amount is in kobo (smallest unit for NGN) or cents for USD. 
    # We'll assume the currency is handled by Paystack account settings or passing it.
    amount_kobo = int(order.total * 100)
    reference = f"LIZ-{uuid.uuid4().hex[:10].upper()}-{order.id.hex[:5].upper()}"

    paystack_data = {
        "email": current_user.email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": settings.paystack_callback_url,
        "metadata": {
            "order_id": str(order.id),
            "buyer_id": str(current_user.id)
        }
    }

    headers = {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "Content-Type": "application/json"
    }

    # 3. Call Paystack API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json=paystack_data,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            res_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Paystack API error: {str(e)}")

    if not res_data.get("status"):
        raise HTTPException(status_code=400, detail=res_data.get("message", "Failed to initialize transaction"))

    # 4. Save reference to order
    order.payment_reference = reference
    await db.commit()

    return PaymentInitializeResponse(
        authorization_url=res_data["data"]["authorization_url"],
        reference=reference,
        access_code=res_data["data"]["access_code"]
    )

@router.post(
    "/webhook",
    summary="Paystack Webhook Handler",
    description="Endpoint for Paystack to send transaction status updates. Supports signature verification."
)
async def paystack_webhook(
    request: Request, 
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Paystack webhook events."""
    payload = await request.body()
    
    # 1. Verify signature
    if not x_paystack_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    computed_sig = hmac.new(
        settings.paystack_secret_key.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()

    if computed_sig != x_paystack_signature:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Parse event
    event = json.loads(payload)
    
    if event["event"] == "charge.success":
        data = event["data"]
        reference = data.get("reference")
        
        if reference:
            result = await db.execute(select(Order).where(Order.payment_reference == reference))
            order = result.scalar_one_or_none()
            
            if order and order.status == OrderStatus.pending:
                order.status = OrderStatus.paid
                order.payment_id = str(data.get("id")) # Paystack transaction ID
                await db.commit()
                # Here you could trigger email notifications or order processing
                
    return {"status": "success"}

@router.get(
    "/verify/{reference}",
    summary="Verify Transaction",
    description="Manually verify the status of a transaction using its reference. Useful as a fallback for redirection callbacks."
)
async def verify_payment(reference: str, db: AsyncSession = Depends(get_db)):
    """Manual verification endpoint (fallback for callback url)"""
    headers = {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers=headers
            )
            response.raise_for_status()
            res_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Paystack verification error: {str(e)}")

    if res_data.get("status") and res_data["data"]["status"] == "success":
        result = await db.execute(select(Order).where(Order.payment_reference == reference))
        order = result.scalar_one_or_none()
        if order and order.status == OrderStatus.pending:
            order.status = OrderStatus.paid
            order.payment_id = str(res_data["data"]["id"])
            await db.commit()
            return {"status": "paid", "order_id": order.id}
            
    return {"status": "pending_or_failed"}
