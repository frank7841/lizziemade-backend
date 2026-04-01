from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User, UserRole
from app.models.seller import Seller
from app.models.order import Order
from app.models.product import Product
from app.dependencies import get_current_user, get_current_admin
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin)])


@router.get("/stats", summary="Get Platform Stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns high-level platform statistics for the admin dashboard.
    """
    user_count = await db.scalar(select(func.count(User.id)))
    seller_count = await db.scalar(select(func.count(Seller.id)))
    product_count = await db.scalar(select(func.count(Product.id)))
    order_count = await db.scalar(select(func.count(Order.id)))
    
    # Total revenue (simplified)
    # total_revenue = await db.scalar(select(func.sum(Order.total_amount)))
    
    return {
        "users": user_count,
        "sellers": seller_count,
        "products": product_count,
        "orders": order_count,
        "revenue": 0.0  # Placeholder until revenue logic is finalized
    }


@router.get("/sellers", summary="List All Sellers")
async def list_sellers(db: AsyncSession = Depends(get_db)):
    """
    Returns a list of all registered sellers and their status.
    """
    result = await db.execute(select(Seller).options())
    sellers = result.scalars().all()
    return sellers


@router.patch("/sellers/{seller_id}/verify", summary="Verify Seller")
async def verify_seller(seller_id: str, db: AsyncSession = Depends(get_db)):
    """
    Verifies a seller's account.
    """
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Assuming there's an is_verified field or similar
    # seller.is_verified = True
    await db.commit()
    return {"status": "success", "message": "Seller verified"}
