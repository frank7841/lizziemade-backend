from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ShippingAddress(BaseModel):
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    country: str
    postal_code: str
    phone: Optional[str] = None


class OrderItemCreate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    custom_order_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    quantity: int = 1
    customization_notes: Optional[str] = None


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    shipping_address: ShippingAddress
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: uuid.UUID
    status: OrderStatus
    subtotal: float
    shipping_fee: float
    total: float
    shipping_address: Optional[dict]
    stripe_payment_intent: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subtotal = 0.0
    items_to_add = []

    for item in payload.items:
        if item.product_id:
            result = await db.execute(select(Product).where(Product.id == item.product_id))
            product = result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            unit_price = product.price
            subtotal += unit_price * item.quantity
            items_to_add.append((item, unit_price))

    shipping_fee = 0.0  # Calculated by seller / flat rate
    total = subtotal + shipping_fee

    order = Order(
        buyer_id=current_user.id,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
        shipping_address=payload.shipping_address.model_dump(),
        notes=payload.notes,
    )
    db.add(order)
    await db.flush()

    for item, unit_price in items_to_add:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            custom_order_id=item.custom_order_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=unit_price,
            customization_notes=item.customization_notes,
        )
        db.add(order_item)

    await db.commit()
    await db.refresh(order)
    return order


@router.get("/", response_model=list[OrderOut])
async def list_my_orders(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.buyer_id == current_user.id).order_by(Order.created_at.desc()))
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id, Order.buyer_id == current_user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id, Order.buyer_id == current_user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in [OrderStatus.pending]:
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")
    order.status = OrderStatus.cancelled
    await db.commit()
    await db.refresh(order)
    return order
