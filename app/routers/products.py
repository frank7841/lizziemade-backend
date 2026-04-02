from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database import get_db
from app.models.product import Product, ProductVariant, Category, DifficultyLevel
from app.models.seller import Seller
from app.dependencies import get_current_user, get_current_seller, get_current_seller_or_admin
from app.models.user import User, UserRole

router = APIRouter(prefix="/products", tags=["Products"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


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
    category_id: uuid.UUID
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
    seller_id: Optional[uuid.UUID] = None  # Admin only
    dimensions: Optional[dict] = None  # {"length": 10, "width": 5, "unit": "cm"}


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    category_id: uuid.UUID | None = None
    stock: int | None = None
    is_active: bool | None = None
    tags: list[str] | None = None
    images: list[dict] | None = None
    is_digital: bool | None = None
    difficulty_level: Optional[DifficultyLevel] = None
    file_url: Optional[str] = None
    seller_id: Optional[uuid.UUID] = None  # Admin only
    dimensions: Optional[dict] = None


class ProductOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    price: float
    category_id: uuid.UUID | None
    category: Optional[CategoryOut] = None
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
    dimensions: Optional[dict] = None

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
    category_slug: Optional[str] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
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
    if category_id:
        query = query.where(Product.category_id == category_id)
    elif category_slug:
        query = query.join(Product.category).where(Category.slug == category_slug)
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
    current_user: User = Depends(get_current_seller_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.admin and payload.seller_id:
        seller_id = payload.seller_id
        # Verify seller exists
        seller_result = await db.execute(select(Seller).where(Seller.id == seller_id))
        if not seller_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Target seller not found")
    else:
        # Get seller profile for current user (seller or admin-acting-as-seller)
        result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
        seller = result.scalar_one_or_none()
        if not seller:
            if current_user.role == UserRole.admin:
                raise HTTPException(status_code=400, detail="seller_id is required for admin product creation if no personal seller profile exists")
            raise HTTPException(status_code=404, detail="Seller profile not found")
        seller_id = seller.id

    # Verify category exists
    cat_result = await db.execute(select(Category).where(Category.id == payload.category_id))
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        seller_id=seller_id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category_id=payload.category_id,
        tags=payload.tags,
        materials=payload.materials,
        is_customizable=payload.is_customizable,
        stock=payload.stock,
        images=payload.images,
        is_digital=payload.is_digital,
        difficulty_level=payload.difficulty_level,
        file_url=payload.file_url,
        dimensions=payload.dimensions,
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
    current_user: User = Depends(get_current_seller_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify ownership or admin status
    if current_user.role != UserRole.admin:
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
    current_user: User = Depends(get_current_seller_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role != UserRole.admin:
        seller_result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
        seller = seller_result.scalar_one_or_none()
        if not seller or product.seller_id != seller.id:
            raise HTTPException(status_code=403, detail="Not your product")

    product.is_active = False  # Soft delete
    await db.commit()
