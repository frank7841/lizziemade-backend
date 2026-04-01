import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from app.database import Base


class CustomOrderStatus(str, enum.Enum):
    pending = "pending"         # Buyer submitted request
    quoted = "quoted"           # Seller sent a price quote
    accepted = "accepted"       # Buyer accepted the quote
    rejected = "rejected"       # Buyer rejected the quote
    in_production = "in_production"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class CustomOrder(Base):
    __tablename__ = "custom_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)  # [{"url": ..., "public_id": ...}]
    colour_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buyer_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    quoted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    seller_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Seller's response / quote note
    status: Mapped[CustomOrderStatus] = mapped_column(SAEnum(CustomOrderStatus), default=CustomOrderStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id], back_populates="sent_custom_orders")
    seller: Mapped["Seller"] = relationship("Seller", foreign_keys=[seller_id], back_populates="received_custom_orders")

    def __repr__(self) -> str:
        return f"<CustomOrder {self.title} [{self.status}]>"
