from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import date, datetime
from app.database import get_db
from app.models.shipment import Shipment, ShipmentStatus
from app.models.order import Order, OrderStatus
from app.dependencies import get_current_user, get_current_seller
from app.models.seller import Seller
from app.models.user import User

router = APIRouter(prefix="/shipments", tags=["Shipments"])


class ShipmentCreate(BaseModel):
    order_id: uuid.UUID
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    estimated_delivery: Optional[date] = None


class TrackingEventAdd(BaseModel):
    status: str
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None


class ShipmentOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    carrier: Optional[str]
    tracking_number: Optional[str]
    tracking_url: Optional[str]
    status: ShipmentStatus
    estimated_delivery: Optional[date]
    events: Optional[list]
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/", response_model=ShipmentOut, status_code=201)
async def create_shipment(
    payload: ShipmentCreate,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    shipment = Shipment(
        order_id=payload.order_id,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        tracking_url=payload.tracking_url,
        estimated_delivery=payload.estimated_delivery,
        status=ShipmentStatus.shipped,
        events=[],
    )
    db.add(shipment)
    order.status = OrderStatus.shipped
    await db.commit()
    await db.refresh(shipment)
    return shipment


@router.get("/{order_id}", response_model=ShipmentOut)
async def track_shipment(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment).where(Shipment.order_id == order_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.post("/{shipment_id}/events", response_model=ShipmentOut)
async def add_tracking_event(
    shipment_id: uuid.UUID,
    payload: TrackingEventAdd,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    event = {
        "status": payload.status,
        "location": payload.location,
        "description": payload.description,
        "timestamp": (payload.timestamp or datetime.utcnow()).isoformat(),
    }
    shipment.events = (shipment.events or []) + [event]

    if payload.status == "delivered":
        shipment.status = ShipmentStatus.delivered
        shipment.delivered_at = datetime.utcnow()
        order_result = await db.execute(select(Order).where(Order.id == shipment.order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.delivered

    await db.commit()
    await db.refresh(shipment)
    return shipment
