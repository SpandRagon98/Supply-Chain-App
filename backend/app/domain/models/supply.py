"""Supplier, material, product, BOM, facility, and inventory models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from app.domain.enums import FacilityType, RecordStatus


class Supplier(TenantEntity):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(240))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, length=16),
        default=RecordStatus.ACTIVE,
        nullable=False,
    )
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)


class SupplierSite(TenantEntity):
    __tablename__ = "supplier_sites"
    __table_args__ = (UniqueConstraint("organization_id", "supplier_id", "code"),)

    supplier_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    capacity_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SupplierRating(TenantEntity):
    __tablename__ = "supplier_ratings"
    __table_args__ = (UniqueConstraint("organization_id", "supplier_id", "rating_date"),)

    supplier_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating_date: Mapped[date] = mapped_column(Date, nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    delivery_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    resilience_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    factors: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(100), default="INTERNAL", nullable=False)


class Material(TenantEntity):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("organization_id", "sku"),)

    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    standard_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MaterialSupplier(TenantEntity):
    __tablename__ = "material_suppliers"
    __table_args__ = (UniqueConstraint("organization_id", "material_id", "supplier_site_id"),)

    material_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("supplier_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_material_code: Mapped[str | None] = mapped_column(String(100))
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_order_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    monthly_capacity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    allocated_capacity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(TenantEntity):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "sku"),)

    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)
    standard_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BillOfMaterial(TenantEntity):
    __tablename__ = "bills_of_material"
    __table_args__ = (UniqueConstraint("organization_id", "product_id", "version"),)

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BOMComponent(TenantEntity):
    __tablename__ = "bom_components"
    __table_args__ = (
        CheckConstraint(
            "(material_id IS NOT NULL AND component_product_id IS NULL) OR "
            "(material_id IS NULL AND component_product_id IS NOT NULL)",
            name="component_material_xor_product",
        ),
        UniqueConstraint(
            "organization_id", "bill_of_material_id", "line_number", name="uq_bom_component_line"
        ),
    )

    bill_of_material_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bills_of_material.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), index=True
    )
    component_product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    scrap_factor: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    substitution_group: Mapped[str | None] = mapped_column(String(80))


class Facility(TenantEntity):
    __tablename__ = "facilities"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    facility_type: Mapped[FacilityType] = mapped_column(
        Enum(FacilityType, native_enum=False, length=32), nullable=False
    )
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __mapper_args__ = {"polymorphic_on": facility_type, "polymorphic_abstract": True}


class Plant(Facility):
    __mapper_args__ = {"polymorphic_identity": FacilityType.PLANT}


class Warehouse(Facility):
    __mapper_args__ = {"polymorphic_identity": FacilityType.WAREHOUSE}


class DistributionCenter(Facility):
    __mapper_args__ = {"polymorphic_identity": FacilityType.DISTRIBUTION_CENTER}


class InventorySnapshot(TenantEntity):
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        CheckConstraint(
            "(material_id IS NOT NULL AND product_id IS NULL) OR "
            "(material_id IS NULL AND product_id IS NOT NULL)",
            name="inventory_material_xor_product",
        ),
    )

    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    on_hand_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    in_transit_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    safety_stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=0, nullable=False
    )
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))


class ConsumptionHistory(TenantEntity):
    __tablename__ = "consumption_history"
    __table_args__ = (
        CheckConstraint(
            "(material_id IS NOT NULL AND product_id IS NULL) OR "
            "(material_id IS NULL AND product_id IS NOT NULL)",
            name="consumption_material_xor_product",
        ),
        UniqueConstraint(
            "organization_id", "facility_id", "material_id", "product_id", "period_start"
        ),
    )

    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))
