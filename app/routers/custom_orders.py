from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database import get_db
from app.models.custom_order import CustomOrder, CustomOrderStatus
from app.models.seller import Seller
from app.dependencies import get_current_user, get_current_seller
from app.models.user import User
from datetime import datetime

router = APIRouter(prefix="/custom-orders", tags=["Custom Orders"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CustomOrderCreate(BaseModel):
    seller_id: uuid.UUID
    title: str
    description: str
    colour_preferences: Optional[str] = None
    size_notes: Optional[str] = None
    desired_deadline: Optional[datetime] = None
    buyer_budget: Optional[float] = None


class QuotePayload(BaseModel):
    quoted_price: float
    seller_notes: Optional[str] = None


class CustomOrderOut(BaseModel):
    id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: str
    status: CustomOrderStatus
    buyer_budget: Optional[float]
    quoted_price: Optional[float]
    seller_notes: Optional[str]
    desired_deadline: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=CustomOrderOut, status_code=201)
async def create_custom_order(
    payload: CustomOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify seller exists
    seller_result = await db.execute(select(Seller).where(Seller.id == payload.seller_id))
    if not seller_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Seller not found")

    order = CustomOrder(
        buyer_id=current_user.id,
        seller_id=payload.seller_id,
        title=payload.title,
        description=payload.description,
        colour_preferences=payload.colour_preferences,
        size_notes=payload.size_notes,
        desired_deadline=payload.desired_deadline,
        buyer_budget=payload.buyer_budget,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/my", response_model=list[CustomOrderOut])
async def my_custom_orders(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CustomOrder).where(CustomOrder.buyer_id == current_user.id))
    return result.scalars().all()


@router.get("/incoming", response_model=list[CustomOrderOut])
async def incoming_custom_orders(current_user: User = Depends(get_current_seller), db: AsyncSession = Depends(get_db)):
    seller_result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
    seller = seller_result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")

    result = await db.execute(select(CustomOrder).where(CustomOrder.seller_id == seller.id))
    return result.scalars().all()


@router.patch("/{order_id}/quote", response_model=CustomOrderOut)
async def quote_custom_order(
    order_id: uuid.UUID,
    payload: QuotePayload,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CustomOrder).where(CustomOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Custom order not found")
    if order.status != CustomOrderStatus.pending:
        raise HTTPException(status_code=400, detail="Can only quote a pending order")

    order.quoted_price = payload.quoted_price
    order.seller_notes = payload.seller_notes
    order.status = CustomOrderStatus.quoted
    await db.commit()
    await db.refresh(order)
    return order


@router.patch("/{order_id}/accept", response_model=CustomOrderOut)
async def accept_quote(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CustomOrder).where(CustomOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.buyer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != CustomOrderStatus.quoted:
        raise HTTPException(status_code=400, detail="No quote to accept yet")

    order.status = CustomOrderStatus.accepted
    await db.commit()
    await db.refresh(order)
    return order


@router.patch("/{order_id}/reject", response_model=CustomOrderOut)
async def reject_quote(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CustomOrder).where(CustomOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.buyer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = CustomOrderStatus.rejected
    await db.commit()
    await db.refresh(order)
    return order
