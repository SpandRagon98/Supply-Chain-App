"""Procurement, logistics, customer, and order models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import TenantEntity
from app.domain.enums import OrderStatus, ShipmentStatus


class PurchaseOrder(TenantEntity):
    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("organization_id", "order_number"),)

    order_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier_site_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("supplier_sites.id", ondelete="SET NULL"), index=True
    )
    destination_facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32), nullable=False
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class PurchaseOrderLine(TenantEntity):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        CheckConstraint(
            "(material_id IS NOT NULL AND product_id IS NULL) OR "
            "(material_id IS NULL AND product_id IS NOT NULL)",
            name="po_line_material_xor_product",
        ),
        UniqueConstraint("organization_id", "purchase_order_id", "line_number"),
    )

    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32), nullable=False
    )


class Shipment(TenantEntity):
    __tablename__ = "shipments"
    __table_args__ = (UniqueConstraint("organization_id", "shipment_number"),)

    shipment_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    purchase_order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), index=True
    )
    origin_supplier_site_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("supplier_sites.id", ondelete="SET NULL"), index=True
    )
    origin_facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facilities.id", ondelete="SET NULL"), index=True
    )
    destination_facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, native_enum=False, length=24), nullable=False
    )
    transportation_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(160))
    tracking_reference: Mapped[str | None] = mapped_column(String(160))
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_location: Mapped[str | None] = mapped_column(String(240))
    contents: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    source_reference: Mapped[str | None] = mapped_column(String(255))


class ShipmentEvent(TenantEntity):
    __tablename__ = "shipment_events"
    __table_args__ = (UniqueConstraint("organization_id", "shipment_id", "source_event_id"),)

    shipment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    location: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)


class Customer(TenantEntity):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    segment: Mapped[str | None] = mapped_column(String(100))
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    currency: Mapped[str | None] = mapped_column(String(3))


class CustomerOrder(TenantEntity):
    __tablename__ = "customer_orders"
    __table_args__ = (UniqueConstraint("organization_id", "order_number"),)

    order_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fulfillment_facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facilities.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32), nullable=False
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_delivery_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))


class CustomerOrderLine(TenantEntity):
    __tablename__ = "customer_order_lines"
    __table_args__ = (UniqueConstraint("organization_id", "customer_order_id", "line_number"),)

    customer_order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customer_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fulfilled_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    promised_date: Mapped[date | None] = mapped_column(Date)
