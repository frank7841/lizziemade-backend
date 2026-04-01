import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from app.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    in_production = "in_production"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.pending)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    shipping_fee: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True) # Paystack transaction reference
    payment_id: Mapped[str | None] = mapped_column(String(200), nullable=True)        # Paystack external transaction ID
    shipping_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {name, line1, line2, city, country, postal_code}
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    buyer: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="order", uselist=False)
    review: Mapped["Review"] = relationship("Review", back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<Order {self.id} [{self.status}]>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    custom_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("custom_orders.id"), nullable=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    customization_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
