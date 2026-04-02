from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.product import Category
from app.models.user import User, UserRole
from app.dependencies import get_current_admin
from pydantic import BaseModel
import uuid
from typing import Optional

router = APIRouter(prefix="/categories", tags=["Categories"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[CategoryOut], summary="List All Categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    Retrieves all product categories. Publicly accessible.
    """
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.post(
    "/", 
    response_model=CategoryOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Category (Admin Only)",
    dependencies=[Depends(get_current_admin)]
)
async def create_category(payload: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new product category. Restricted to administrators.
    """
    # Check if duplicate name or slug
    existing = await db.execute(select(Category).where((Category.name == payload.name) | (Category.slug == payload.slug)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category with this name or slug already exists")

    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch(
    "/{category_id}", 
    response_model=CategoryOut,
    summary="Update Category (Admin Only)",
    dependencies=[Depends(get_current_admin)]
)
async def update_category(category_id: uuid.UUID, payload: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    """
    Updates an existing product category. Restricted to administrators.
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete(
    "/{category_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Category (Admin Only)",
    dependencies=[Depends(get_current_admin)]
)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Deletes a product category. Restricted to administrators. 
    Note: Products linked to this category will have their category_id set to NULL.
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(category)
    await db.commit()
    return None
