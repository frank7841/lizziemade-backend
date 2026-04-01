import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    shop_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_sales: Mapped[int] = mapped_column(default=0)
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {instagram, facebook, tiktok}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="seller_profile")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="seller")
    received_custom_orders: Mapped[list["CustomOrder"]] = relationship(
        "CustomOrder", foreign_keys="CustomOrder.seller_id", back_populates="seller"
    )

    def __repr__(self) -> str:
        return f"<Seller {self.shop_name}>"
