from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database import get_db
from app.models.product import Product, ProductVariant, ProductCategory, DifficultyLevel
from app.models.seller import Seller
from app.dependencies import get_current_user, get_current_seller
from app.models.user import User

router = APIRouter(prefix="/products", tags=["Products"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class VariantCreate(BaseModel):
    colour: str | None = None
    size: str | None = None
    material: str | None = None
    price_delta: float = 0.0
    stock: int = 0


class ProductCreate(BaseModel):
    title: str
    description: str
    price: float
    category: ProductCategory
    tags: list[str] = []
    materials: list[str] = []
    is_customizable: bool = False
    stock: int = 1
    images: list[dict] = []
    variants: list[VariantCreate] = []

    # New Fields
    is_digital: bool = False
    difficulty_level: Optional[DifficultyLevel] = None
    file_url: Optional[str] = None


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    is_active: bool | None = None
    tags: list[str] | None = None
    images: list[dict] | None = None
    is_digital: bool | None = None
    difficulty_level: Optional[DifficultyLevel] = None
    file_url: Optional[str] = None


class ProductOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    price: float
    category: str
    tags: list
    images: list
    materials: list
    is_customizable: bool
    stock: int
    rating: float
    review_count: int
    seller_id: uuid.UUID
    is_digital: bool
    difficulty_level: Optional[DifficultyLevel] = None
    file_url: Optional[str] = None

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/", 
    response_model=list[ProductOut],
    summary="List All Products",
    description="Retrieves a paginated list of all active products with support for searching and filtering by category, price, and customizability."
)
async def list_products(
    search: Optional[str] = Query(None),
    category: Optional[ProductCategory] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    is_customizable: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_active == True)

    if search:
        query = query.where(
            or_(
                Product.title.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.where(Product.category == category)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if is_customizable is not None:
        query = query.where(Product.is_customizable == is_customizable)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post(
    "/", 
    response_model=ProductOut, 
    status_code=201,
    summary="Create New Product",
    description="Allows an authenticated seller to create a new product listing, including optional variants (size, colour, etc.)."
)
async def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    # Get seller profile
    result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")

    product = Product(
        seller_id=seller.id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        tags=payload.tags,
        materials=payload.materials,
        is_customizable=payload.is_customizable,
        stock=payload.stock,
        images=payload.images,
        is_digital=payload.is_digital,
        difficulty_level=payload.difficulty_level,
        file_url=payload.file_url,
    )
    db.add(product)
    await db.flush()

    for v in payload.variants:
        variant = ProductVariant(product_id=product.id, **v.model_dump())
        db.add(variant)

    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify ownership
    seller_result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
    seller = seller_result.scalar_one_or_none()
    if not seller or product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not your product")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    seller_result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
    seller = seller_result.scalar_one_or_none()
    if not seller or product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not your product")

    product.is_active = False  # Soft delete
    await db.commit()
