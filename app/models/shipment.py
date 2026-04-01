import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from app.database import Base


class ShipmentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    shipped = "shipped"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    returned = "returned"


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)          # e.g. DHL, Posta Kenya, J&T
    tracking_number: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ShipmentStatus] = mapped_column(SAEnum(ShipmentStatus), default=ShipmentStatus.pending)
    estimated_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Timeline events: [{"status": ..., "location": ..., "timestamp": ..., "description": ...}]
    events: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="shipment")

    def __repr__(self) -> str:
        return f"<Shipment {self.tracking_number} [{self.status}]>"
