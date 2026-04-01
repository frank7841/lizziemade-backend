"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("role", sa.Enum("buyer", "seller", "admin", name="userrole"), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Sellers
    op.create_table(
        "sellers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_name", sa.String(150), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("banner_url", sa.String(500), nullable=True),
        sa.Column("location", sa.String(150), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_sales", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("social_links", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("shop_name"),
    )

    # Products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("category", sa.Enum("amigurumi","clothing","accessories","home_decor","bags","baby_items","patterns","other", name="productcategory"), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=True),
        sa.Column("materials", postgresql.JSONB(), nullable=True),
        sa.Column("is_customizable", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_featured", sa.Boolean(), server_default="false"),
        sa.Column("stock", sa.Integer(), server_default="1"),
        sa.Column("rating", sa.Float(), server_default="0"),
        sa.Column("review_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_title", "products", ["title"])

    # Product Variants
    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("colour", sa.String(80), nullable=True),
        sa.Column("size", sa.String(40), nullable=True),
        sa.Column("material", sa.String(100), nullable=True),
        sa.Column("price_delta", sa.Float(), server_default="0"),
        sa.Column("stock", sa.Integer(), server_default="0"),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )

    # Custom Orders
    op.create_table(
        "custom_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("attachments", postgresql.JSONB(), nullable=True),
        sa.Column("colour_preferences", sa.Text(), nullable=True),
        sa.Column("size_notes", sa.Text(), nullable=True),
        sa.Column("desired_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buyer_budget", sa.Float(), nullable=True),
        sa.Column("quoted_price", sa.Float(), nullable=True),
        sa.Column("seller_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("pending","quoted","accepted","rejected","in_production","shipped","delivered","cancelled", name="customorderstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Orders
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("pending","paid","in_production","shipped","delivered","cancelled","refunded", name="orderstatus"), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("shipping_fee", sa.Float(), server_default="0"),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("stripe_payment_intent", sa.String(200), nullable=True),
        sa.Column("stripe_charge_id", sa.String(200), nullable=True),
        sa.Column("shipping_address", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Order Items
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custom_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("customization_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["custom_order_id"], ["custom_orders.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Shipments
    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier", sa.String(100), nullable=True),
        sa.Column("tracking_number", sa.String(200), nullable=True),
        sa.Column("tracking_url", sa.String(500), nullable=True),
        sa.Column("status", sa.Enum("pending","processing","shipped","in_transit","out_for_delivery","delivered","failed","returned", name="shipmentstatus"), nullable=False),
        sa.Column("estimated_delivery", sa.Date(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_shipments_tracking", "shipments", ["tracking_number"])

    # Reviews
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("reviews")
    op.drop_table("shipments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("custom_orders")
    op.drop_table("product_variants")
    op.drop_table("products")
    op.drop_table("sellers")
    op.drop_table("users")
