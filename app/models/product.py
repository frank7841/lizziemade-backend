import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from app.database import Base


class ProductCategory(str, enum.Enum):
    amigurumi = "amigurumi"
    clothing = "clothing"
    accessories = "accessories"
    home_decor = "home_decor"
    bags = "bags"
    baby_items = "baby_items"
    patterns = "patterns"
    other = "other"


class DifficultyLevel(str, enum.Enum):
    beginner = "beginner"
    easy = "easy"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[ProductCategory] = mapped_column(SAEnum(ProductCategory), nullable=False)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)          # ["soft", "handmade", ...]
    images: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)         # [{"url": ..., "public_id": ...}]
    materials: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)      # ["cotton", "acrylic"]
    is_customizable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    stock: Mapped[int] = mapped_column(Integer, default=1)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)

    # Pattern/Digital Specific
    is_digital: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty_level: Mapped[DifficultyLevel | None] = mapped_column(SAEnum(DifficultyLevel), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # URL for digital patterns

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    seller: Mapped["Seller"] = relationship("Seller", back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product {self.title}>"


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    colour: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)      # XS, S, M, L, XL or cm dimensions
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_delta: Mapped[float] = mapped_column(Float, default=0.0)           # Added to base price
    stock: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
