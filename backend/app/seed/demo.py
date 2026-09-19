"""Deterministic Nova Electronics demonstration dataset."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.base import EntityBase
from app.domain.enums import (
    ApprovalStatus,
    ConnectorStatus,
    ExecutionStatus,
    FacilityType,
    FailurePolicy,
    IncidentStatus,
    OrderStatus,
    RiskBand,
    RoleKey,
    ScenarioStatus,
    Severity,
    ShipmentStatus,
    SignalCategory,
    WorkflowVersionStatus,
)
from app.domain.models import (
    ApprovalRequest,
    AuditLog,
    BillOfMaterial,
    BOMComponent,
    Connector,
    ConsumptionHistory,
    Customer,
    CustomerOrder,
    CustomerOrderLine,
    DisruptionIncident,
    DistributionCenter,
    ExecutionAction,
    Facility,
    ImpactAssessment,
    ImpactMetric,
    InventorySnapshot,
    LLMModelConfiguration,
    Material,
    MaterialSupplier,
    Organization,
    Plant,
    Product,
    PromptTemplate,
    PurchaseOrder,
    PurchaseOrderLine,
    Recommendation,
    RiskAssessment,
    Role,
    Scenario,
    ScenarioAction,
    Shipment,
    ShipmentEvent,
    SignalSource,
    StageConfiguration,
    StageDefinition,
    StageDependency,
    Supplier,
    SupplierRating,
    SupplierSite,
    User,
    UserRole,
    Warehouse,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.infrastructure.database import async_session_factory

SEED_NAMESPACE = "https://supply-chain-autopilot.example/demo/nova-electronics"
SNAPSHOT_AT = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


def demo_id(kind: str, key: str) -> UUID:
    """Return a stable identity so repeated seeding updates rather than duplicates."""

    return uuid5(NAMESPACE_URL, f"{SEED_NAMESPACE}:{kind}:{key}")


def decimal(value: int | float | str) -> Decimal:
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class DemoDataset:
    """Entities grouped in foreign-key-safe persistence stages."""

    stages: tuple[tuple[EntityBase, ...], ...]

    @property
    def entities(self) -> tuple[EntityBase, ...]:
        return tuple(entity for stage in self.stages for entity in stage)

    @property
    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(type(entity).__name__ for entity in self.entities).items()))


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    organization_id: UUID
    counts: dict[str, int]
    total_entities: int


SUPPLIER_SPECS = (
    ("FORMOSA", "Formosa Silicon Works", "TW", "Tainan", 96),
    ("HANSEONG", "Hanseong Semiconductors", "KR", "Icheon", 88),
    ("TEXCHIP", "Texas Chipworks", "US", "Austin", 84),
    ("OSAKA-IC", "Osaka Integrated Circuits", "JP", "Osaka", 90),
    ("KYOTO-BATT", "Kyoto Battery Systems", "JP", "Kyoto", 94),
    ("VOLTEDGE", "VoltEdge Energy", "MY", "Penang", 78),
    ("SEOUL-DISPLAY", "Seoul Display Technologies", "KR", "Paju", 82),
    ("SHENZHEN-DISPLAY", "Shenzhen Vision Panels", "CN", "Shenzhen", 80),
    ("ALPS-MEM", "Alps Memory Corporation", "JP", "Nagano", 86),
    ("SINGA-STORAGE", "Singapore Storage Systems", "SG", "Singapore", 77),
    ("DECCAN-PCB", "Deccan Precision Circuits", "IN", "Hyderabad", 74),
    ("PUNE-METAL", "Pune Precision Metals", "IN", "Pune", 70),
    ("CHENNAI-CABLE", "Chennai Cable Works", "IN", "Chennai", 66),
    ("BLR-THERMAL", "Bengaluru Thermal Solutions", "IN", "Bengaluru", 72),
    ("DELHI-ELECTRO", "Delhi Electromech", "IN", "Delhi", 68),
    ("VIETKEY", "VietKey Components", "VN", "Ho Chi Minh City", 64),
    ("SHENZHEN-OPTICS", "Shenzhen Optics Group", "CN", "Shenzhen", 69),
    ("MUMBAI-PACK", "Mumbai Sustainable Packaging", "IN", "Mumbai", 45),
)


MATERIAL_SPECS = (
    ("CPU-X9", "X9 Performance Processor", "SEMICONDUCTOR", 26500, 100, ("FORMOSA", "HANSEONG")),
    ("CPU-U7", "U7 Mobile Processor", "SEMICONDUCTOR", 18400, 96, ("FORMOSA", "TEXCHIP")),
    ("PWR-IC-42", "PMX-42 Power Management IC", "SEMICONDUCTOR", 1220, 98, ("FORMOSA", "OSAKA-IC")),
    ("CHIPSET-PRO", "Pro Platform Chipset", "SEMICONDUCTOR", 6400, 91, ("OSAKA-IC", "HANSEONG")),
    ("MCU-IOT", "Industrial Gateway MCU", "SEMICONDUCTOR", 2950, 88, ("OSAKA-IC", "TEXCHIP")),
    ("BMS-IC", "Battery Management Controller", "SEMICONDUCTOR", 860, 92, ("OSAKA-IC", "FORMOSA")),
    ("DRAM-16", "16 GB LPDDR5 Module", "MEMORY", 4150, 82, ("ALPS-MEM", "HANSEONG")),
    ("DRAM-8", "8 GB LPDDR5 Module", "MEMORY", 2320, 74, ("ALPS-MEM", "HANSEONG")),
    ("NVME-1TB", "1 TB NVMe Storage", "STORAGE", 5350, 76, ("SINGA-STORAGE", "ALPS-MEM")),
    ("NVME-512", "512 GB NVMe Storage", "STORAGE", 3180, 68, ("SINGA-STORAGE", "ALPS-MEM")),
    ("EMMC-128", "128 GB Industrial eMMC", "STORAGE", 1850, 72, ("SINGA-STORAGE",)),
    ("PCB-PRO", "Pro Motherboard PCB", "PCB", 1420, 79, ("DECCAN-PCB",)),
    ("PCB-AIR", "Air Motherboard PCB", "PCB", 1180, 76, ("DECCAN-PCB",)),
    ("PCB-GATE", "Gateway Controller PCB", "PCB", 780, 71, ("DECCAN-PCB",)),
    (
        "CAP-SET",
        "High Reliability Capacitor Set",
        "ELECTRONICS",
        310,
        62,
        ("DELHI-ELECTRO", "DECCAN-PCB"),
    ),
    ("MOSFET-SET", "Power MOSFET Set", "ELECTRONICS", 540, 70, ("DELHI-ELECTRO", "OSAKA-IC")),
    ("CONN-SET", "Board Connector Set", "ELECTRONICS", 265, 55, ("CHENNAI-CABLE", "DELHI-ELECTRO")),
    (
        "PANEL-14",
        "14-inch High Resolution Panel",
        "DISPLAY",
        8950,
        84,
        ("SEOUL-DISPLAY", "SHENZHEN-DISPLAY"),
    ),
    (
        "PANEL-13",
        "13-inch Low Power Panel",
        "DISPLAY",
        7420,
        81,
        ("SEOUL-DISPLAY", "SHENZHEN-DISPLAY"),
    ),
    (
        "PANEL-24",
        "24-inch Professional Panel",
        "DISPLAY",
        12600,
        69,
        ("SHENZHEN-DISPLAY", "SEOUL-DISPLAY"),
    ),
    ("CELL-LI6", "High Density Lithium Cell", "BATTERY", 1680, 99, ("KYOTO-BATT",)),
    ("CELL-LI4", "Low Profile Lithium Cell", "BATTERY", 1490, 95, ("KYOTO-BATT", "VOLTEDGE")),
    ("CHASSIS-14", "Machined 14-inch Chassis", "MECHANICAL", 3820, 61, ("PUNE-METAL",)),
    ("CHASSIS-13", "Machined 13-inch Chassis", "MECHANICAL", 3350, 58, ("PUNE-METAL",)),
    ("CHASSIS-DESK", "Desktop Workstation Chassis", "MECHANICAL", 5240, 52, ("PUNE-METAL",)),
    ("GATE-ENC", "Rugged Gateway Enclosure", "MECHANICAL", 2480, 64, ("PUNE-METAL",)),
    ("KEYBOARD-14", "Backlit Keyboard 14", "INPUT", 1850, 54, ("VIETKEY",)),
    ("KEYBOARD-13", "Backlit Keyboard 13", "INPUT", 1690, 52, ("VIETKEY",)),
    ("CAMERA-HD", "HD Camera Module", "OPTICS", 980, 48, ("SHENZHEN-OPTICS",)),
    ("WIFI-6E", "Wi-Fi 6E Radio Module", "NETWORK", 1450, 67, ("TEXCHIP", "SHENZHEN-OPTICS")),
    ("ANTENNA-SET", "Wireless Antenna Set", "NETWORK", 390, 45, ("CHENNAI-CABLE",)),
    ("FAN-SLIM", "Slim Cooling Fan", "THERMAL", 720, 56, ("BLR-THERMAL",)),
    ("HEATSINK-PRO", "Vapor Chamber Heat Sink", "THERMAL", 1380, 63, ("BLR-THERMAL",)),
    ("PSU-180", "180W Desktop Power Supply", "POWER", 2860, 57, ("DELHI-ELECTRO",)),
    ("ADAPTER-65", "65W USB-C Power Adapter", "POWER", 1950, 59, ("DELHI-ELECTRO",)),
    ("CABLE-SET", "Internal Cable Harness", "CABLE", 460, 42, ("CHENNAI-CABLE",)),
    ("SPEAKER-SET", "Stereo Speaker Set", "AUDIO", 680, 35, ("VIETKEY",)),
    ("TOUCHPAD", "Precision Glass Touchpad", "INPUT", 1320, 50, ("SHENZHEN-OPTICS",)),
    ("PACK-LAP", "Laptop Recycled Packaging", "PACKAGING", 420, 20, ("MUMBAI-PACK",)),
    ("PACK-DESK", "Desktop Recycled Packaging", "PACKAGING", 690, 20, ("MUMBAI-PACK",)),
)


PRODUCT_SPECS = (
    ("ASM-MB-PRO", "Nova Pro Motherboard Assembly", "ASSEMBLY", 38500),
    ("ASM-MB-AIR", "Nova Air Motherboard Assembly", "ASSEMBLY", 27400),
    ("ASM-BAT-72", "Nova 72Wh Battery Pack", "ASSEMBLY", 12400),
    ("ASM-BAT-50", "Nova 50Wh Battery Pack", "ASSEMBLY", 8650),
    ("ASM-DISP-14", "Nova 14-inch Display Assembly", "ASSEMBLY", 10800),
    ("ASM-DISP-13", "Nova 13-inch Display Assembly", "ASSEMBLY", 9150),
    ("NOVABOOK-PRO", "NovaBook Pro 14", "LAPTOP", 129900),
    ("NOVABOOK-AIR", "NovaBook Air 13", "LAPTOP", 89900),
    ("NOVASTATION-X1", "NovaStation X1", "DESKTOP", 159900),
    ("NOVAEDGE-GW", "NovaEdge Industrial Gateway", "IOT", 54900),
)


FACILITY_SPECS = (
    (
        "PUNE-PLANT",
        "Pune Advanced Manufacturing Plant",
        FacilityType.PLANT,
        "Pune",
        "MH",
        decimal("18.5204"),
        decimal("73.8567"),
    ),
    (
        "CHENNAI-PLANT",
        "Chennai Electronics Plant",
        FacilityType.PLANT,
        "Chennai",
        "TN",
        decimal("13.0827"),
        decimal("80.2707"),
    ),
    (
        "BLR-PLANT",
        "Bengaluru Gateway Plant",
        FacilityType.PLANT,
        "Bengaluru",
        "KA",
        decimal("12.9716"),
        decimal("77.5946"),
    ),
    (
        "MUMBAI-WH",
        "Mumbai Import Warehouse",
        FacilityType.WAREHOUSE,
        "Mumbai",
        "MH",
        decimal("19.0760"),
        decimal("72.8777"),
    ),
    (
        "HYD-WH",
        "Hyderabad Component Warehouse",
        FacilityType.WAREHOUSE,
        "Hyderabad",
        "TS",
        decimal("17.3850"),
        decimal("78.4867"),
    ),
    (
        "PUNE-WH",
        "Pune Production Warehouse",
        FacilityType.WAREHOUSE,
        "Pune",
        "MH",
        decimal("18.5679"),
        decimal("73.9143"),
    ),
    (
        "DELHI-DC",
        "Delhi Distribution Center",
        FacilityType.DISTRIBUTION_CENTER,
        "Delhi",
        "DL",
        decimal("28.6139"),
        decimal("77.2090"),
    ),
    (
        "CHENNAI-DC",
        "Chennai Distribution Center",
        FacilityType.DISTRIBUTION_CENTER,
        "Chennai",
        "TN",
        decimal("13.0444"),
        decimal("80.2404"),
    ),
)


CUSTOMER_SPECS = (
    ("CUST-001", "Aster Retail India", 95, "IN", "STRATEGIC"),
    ("CUST-002", "Bharat Digital Stores", 88, "IN", "ENTERPRISE"),
    ("CUST-003", "Crescent Systems", 84, "IN", "ENTERPRISE"),
    ("CUST-004", "DigiSphere Solutions", 91, "IN", "STRATEGIC"),
    ("CUST-005", "Eastern Education Network", 80, "IN", "EDUCATION"),
    ("CUST-006", "Frontier Analytics", 74, "IN", "ENTERPRISE"),
    ("CUST-007", "GreenGrid Energy", 89, "IN", "INDUSTRIAL"),
    ("CUST-008", "Helix Healthcare", 93, "IN", "STRATEGIC"),
    ("CUST-009", "Indus Automation", 82, "IN", "INDUSTRIAL"),
    ("CUST-010", "Jupiter Commerce", 68, "IN", "RETAIL"),
    ("CUST-011", "Kaveri Financial Services", 86, "IN", "ENTERPRISE"),
    ("CUST-012", "Lotus Public Sector Systems", 90, "IN", "GOVERNMENT"),
    ("CUST-013", "Meridian Logistics", 72, "IN", "INDUSTRIAL"),
    ("CUST-014", "NorthStar Telecom", 85, "IN", "ENTERPRISE"),
    ("CUST-015", "Orbit Research Labs", 78, "IN", "RESEARCH"),
    ("CUST-016", "Prism Media Group", 64, "IN", "SMB"),
    ("CUST-017", "Quantum Design Studio", 70, "IN", "SMB"),
    ("CUST-018", "Riverstone Manufacturing", 76, "IN", "INDUSTRIAL"),
)


BOM_SPECS: dict[str, tuple[tuple[str, str, str, bool], ...]] = {
    "ASM-MB-PRO": (
        ("material", "CPU-X9", "1", True),
        ("material", "CHIPSET-PRO", "1", True),
        ("material", "PWR-IC-42", "2", True),
        ("material", "DRAM-16", "2", False),
        ("material", "PCB-PRO", "1", True),
        ("material", "CAP-SET", "1", False),
        ("material", "MOSFET-SET", "1", False),
        ("material", "CONN-SET", "1", False),
        ("material", "WIFI-6E", "1", False),
    ),
    "ASM-MB-AIR": (
        ("material", "CPU-U7", "1", True),
        ("material", "PWR-IC-42", "1", True),
        ("material", "DRAM-8", "2", False),
        ("material", "PCB-AIR", "1", True),
        ("material", "CAP-SET", "1", False),
        ("material", "CONN-SET", "1", False),
        ("material", "WIFI-6E", "1", False),
    ),
    "ASM-BAT-72": (
        ("material", "CELL-LI6", "6", True),
        ("material", "BMS-IC", "1", True),
        ("material", "CABLE-SET", "1", False),
    ),
    "ASM-BAT-50": (
        ("material", "CELL-LI4", "4", True),
        ("material", "BMS-IC", "1", True),
        ("material", "CABLE-SET", "1", False),
    ),
    "ASM-DISP-14": (
        ("material", "PANEL-14", "1", True),
        ("material", "CAMERA-HD", "1", False),
        ("material", "CABLE-SET", "1", False),
    ),
    "ASM-DISP-13": (
        ("material", "PANEL-13", "1", True),
        ("material", "CAMERA-HD", "1", False),
        ("material", "CABLE-SET", "1", False),
    ),
    "NOVABOOK-PRO": (
        ("product", "ASM-MB-PRO", "1", True),
        ("product", "ASM-BAT-72", "1", True),
        ("product", "ASM-DISP-14", "1", True),
        ("material", "NVME-1TB", "1", False),
        ("material", "CHASSIS-14", "1", False),
        ("material", "KEYBOARD-14", "1", False),
        ("material", "TOUCHPAD", "1", False),
        ("material", "SPEAKER-SET", "1", False),
        ("material", "FAN-SLIM", "2", False),
        ("material", "HEATSINK-PRO", "1", False),
        ("material", "ADAPTER-65", "1", False),
        ("material", "PACK-LAP", "1", False),
    ),
    "NOVABOOK-AIR": (
        ("product", "ASM-MB-AIR", "1", True),
        ("product", "ASM-BAT-50", "1", True),
        ("product", "ASM-DISP-13", "1", True),
        ("material", "NVME-512", "1", False),
        ("material", "CHASSIS-13", "1", False),
        ("material", "KEYBOARD-13", "1", False),
        ("material", "TOUCHPAD", "1", False),
        ("material", "SPEAKER-SET", "1", False),
        ("material", "FAN-SLIM", "1", False),
        ("material", "ADAPTER-65", "1", False),
        ("material", "PACK-LAP", "1", False),
    ),
    "NOVASTATION-X1": (
        ("product", "ASM-MB-PRO", "1", True),
        ("material", "NVME-1TB", "1", False),
        ("material", "PANEL-24", "1", False),
        ("material", "CHASSIS-DESK", "1", False),
        ("material", "PSU-180", "1", True),
        ("material", "PACK-DESK", "1", False),
    ),
    "NOVAEDGE-GW": (
        ("material", "MCU-IOT", "1", True),
        ("material", "PWR-IC-42", "1", True),
        ("material", "EMMC-128", "1", False),
        ("material", "PCB-GATE", "1", True),
        ("material", "WIFI-6E", "1", False),
        ("material", "ANTENNA-SET", "2", False),
        ("material", "GATE-ENC", "1", False),
        ("material", "CABLE-SET", "1", False),
    ),
}


def build_demo_dataset(organization_id: UUID | None = None) -> DemoDataset:
    """Build a connected, deterministic Nova Electronics dataset in memory."""

    org_id = organization_id or demo_id("organization", "nova-electronics")
    organization = Organization(
        id=org_id,
        name="Nova Electronics",
        slug="nova-electronics",
        default_currency="INR",
        default_timezone="Asia/Kolkata",
        is_active=True,
    )

    roles = tuple(
        Role(
            id=demo_id("role", role.value),
            organization_id=org_id,
            key=role,
            name=role.value.replace("_", " ").title(),
            description=f"Nova Electronics {role.value.lower()} role",
            is_system=True,
        )
        for role in RoleKey
    )
    user_specs = (
        ("admin@nova.example", "Aarav Mehta", RoleKey.ADMIN),
        ("manager@nova.example", "Meera Iyer", RoleKey.SUPPLY_CHAIN_MANAGER),
        ("planner@nova.example", "Rohan Kulkarni", RoleKey.SUPPLY_CHAIN_PLANNER),
        ("procurement@nova.example", "Kavya Nair", RoleKey.PROCUREMENT),
        ("approver@nova.example", "Vikram Shah", RoleKey.APPROVER),
        ("analyst@nova.example", "Ananya Rao", RoleKey.ANALYST),
        ("viewer@nova.example", "Dev Malhotra", RoleKey.VIEWER),
    )
    users = tuple(
        User(
            id=demo_id("user", email),
            organization_id=org_id,
            email=email,
            display_name=name,
            external_subject=f"demo:{email}",
            is_active=True,
            is_service_account=False,
        )
        for email, name, _role in user_specs
    )
    role_by_key = {role.key: role for role in roles}
    user_by_email = {user.email: user for user in users}
    user_roles = tuple(
        UserRole(
            id=demo_id("user-role", email),
            organization_id=org_id,
            user_id=user_by_email[email].id,
            role_id=role_by_key[role_key].id,
            assigned_by_user_id=user_by_email["admin@nova.example"].id,
        )
        for email, _name, role_key in user_specs
    )

    connector_specs = (
        ("nova-erp", "Nova ERP", "ERP", "mock.erp@1.0"),
        ("global-weather", "Global Weather", "WEATHER", "mock.weather@1.0"),
        ("trusted-news", "Trusted News", "NEWS", "mock.news@1.0"),
        ("ocean-tracking", "Ocean Shipment Tracking", "SHIPMENT", "mock.shipment@1.0"),
        ("supplier-feed", "Supplier Status Feed", "SUPPLIER", "mock.supplier@1.0"),
    )
    connectors = tuple(
        Connector(
            id=demo_id("connector", key),
            organization_id=org_id,
            key=key,
            name=name,
            connector_type=connector_type,
            adapter=adapter,
            status=ConnectorStatus.MOCK_MODE,
            configuration={
                "mode": "mock",
                "batch_size": 100,
                "signal_source_key": key,
            },
        )
        for key, name, connector_type, adapter in connector_specs
    )
    signal_source_configuration: dict[str, object] = {
        "minimum_signal_confidence": 0.2,
        "auto_incident_confidence": 0.7,
        "entity_match_threshold": 0.65,
        "entity_review_threshold": 0.85,
        "incident_dedup_hours": 72,
        "capacity_utilization_threshold": 0.9,
        "inventory_on_hand_threshold": 250,
    }
    signal_sources = tuple(
        SignalSource(
            id=demo_id("signal-source", key),
            organization_id=org_id,
            key=key,
            name=name,
            source_type=connector_type,
            is_active=True,
            configuration=dict(signal_source_configuration),
        )
        for key, name, connector_type, _adapter in connector_specs
    )

    workflow_definition = WorkflowDefinition(
        id=demo_id("workflow-definition", "disruption-response"),
        organization_id=org_id,
        key="disruption-response",
        name="Disruption response",
        description=(
            "Detect, assess, prioritize, recommend, approve, execute, and verify a disruption."
        ),
        is_active=True,
    )
    workflow_version = WorkflowVersion(
        id=demo_id("workflow-version", "disruption-response:1"),
        organization_id=org_id,
        workflow_definition_id=workflow_definition.id,
        version=1,
        status=WorkflowVersionStatus.PUBLISHED,
        published_at=SNAPSHOT_AT,
        published_by_user_id=user_by_email["admin@nova.example"].id,
        change_summary="Canonical governed disruption-response workflow",
    )
    workflow_stage_specs = (
        ("detect-disruption", "Detect disruption", "DETECTION"),
        ("assess-impact", "Assess impact", "IMPACT"),
        ("score-risk", "Score risk", "RISK"),
        ("generate-scenarios", "Generate scenarios", "OPTIMIZATION"),
        ("recommend-action", "Recommend action", "RECOMMENDATION"),
        ("route-approval", "Route approval", "APPROVAL"),
        ("execute-mitigation", "Execute mitigation", "EXECUTION"),
        ("verify-outcome", "Verify outcome", "VERIFICATION"),
    )
    workflow_stages = tuple(
        StageDefinition(
            id=demo_id("workflow-stage", key),
            organization_id=org_id,
            workflow_version_id=workflow_version.id,
            key=key,
            name=name,
            description=f"Deterministic {name.lower()} stage.",
            stage_type=stage_type,
            handler=key,
            handler_version="1.0",
            position=position,
            is_enabled=True,
            input_schema={},
            output_schema={"type": "object"},
            configuration_schema={"type": "object"},
        )
        for position, (key, name, stage_type) in enumerate(workflow_stage_specs)
    )
    workflow_configurations = tuple(
        StageConfiguration(
            id=demo_id("workflow-stage-configuration", stage.key),
            organization_id=org_id,
            stage_definition_id=stage.id,
            configuration={"summary": f"{stage.name} completed"},
            retry_policy={"max_attempts": 2},
            timeout_seconds=300,
            failure_policy=FailurePolicy.FAIL_WORKFLOW,
            approval_requirements=(
                {"required_role": RoleKey.APPROVER.value} if stage.key == "route-approval" else {}
            ),
            ai_configuration={},
        )
        for stage in workflow_stages
    )
    workflow_dependencies = tuple(
        StageDependency(
            id=demo_id("workflow-dependency", f"{previous.key}:{current.key}"),
            organization_id=org_id,
            workflow_version_id=workflow_version.id,
            stage_definition_id=current.id,
            depends_on_stage_id=previous.id,
            condition={},
        )
        for previous, current in zip(workflow_stages, workflow_stages[1:], strict=False)
    )
    llm_configurations = (
        LLMModelConfiguration(
            id=demo_id("llm-configuration", "recommendation-explainer"),
            organization_id=org_id,
            key="recommendation-explainer",
            provider="mock",
            model="deterministic-explainer-v1",
            is_enabled=True,
            parameters={"temperature": 0, "max_output_tokens": 800},
            secret_reference=None,
        ),
    )
    prompt_templates = (
        PromptTemplate(
            id=demo_id("prompt-template", "recommendation-rationale:1"),
            organization_id=org_id,
            key="recommendation-rationale",
            purpose="Explain a deterministic recommendation without changing numeric truth.",
            version=1,
            status=WorkflowVersionStatus.PUBLISHED,
            system_template="Explain only the supplied deterministic result and its lineage.",
            user_template="Summarize recommendation {{ recommendation }}.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            published_at=SNAPSHOT_AT,
        ),
    )
    incident = DisruptionIncident(
        id=demo_id("incident", "taiwan-typhoon-2026"),
        organization_id=org_id,
        incident_number="INC-2026-0915",
        title="Typhoon disruption at Taiwan semiconductor supply base",
        description="Severe weather is constraining production and outbound logistics in Tainan.",
        incident_type=SignalCategory.WEATHER_DISRUPTION,
        severity=Severity.HIGH,
        confidence=decimal("0.96"),
        status=IncidentStatus.APPROVAL_PENDING,
        started_at=SNAPSHOT_AT - timedelta(hours=9),
        expected_end_at=SNAPSHOT_AT + timedelta(days=5),
        affected_location={"city": "Tainan", "country_code": "TW"},
        deduplication_key="weather:tw:tainan:2026-09-15",
        workflow_version_id=workflow_version.id,
    )
    impact_assessment = ImpactAssessment(
        id=demo_id("impact-assessment", "taiwan-typhoon-2026"),
        organization_id=org_id,
        incident_id=incident.id,
        calculated_at=SNAPSHOT_AT,
        calculation_version="1.0",
        summary={
            "affected_supplier": "Formosa Silicon Works",
            "impacted_materials": 5,
            "orders_at_risk": 14,
            "revenue_at_risk": "18450000",
        },
    )
    impact_metrics = (
        ImpactMetric(
            id=demo_id("impact-metric", "taiwan-typhoon:revenue-at-risk"),
            organization_id=org_id,
            assessment_id=impact_assessment.id,
            metric_key="revenue_at_risk",
            numeric_value=decimal("18450000"),
            unit="currency",
            currency="INR",
            lineage=[{"source": "open customer orders", "calculation": "quantity × price"}],
        ),
        ImpactMetric(
            id=demo_id("impact-metric", "taiwan-typhoon:orders-at-risk"),
            organization_id=org_id,
            assessment_id=impact_assessment.id,
            metric_key="customer_orders_at_risk",
            numeric_value=decimal("14"),
            unit="orders",
            lineage=[{"source": "BOM propagation"}],
        ),
    )
    risk_assessment = RiskAssessment(
        id=demo_id("risk-assessment", "taiwan-typhoon-2026"),
        organization_id=org_id,
        incident_id=incident.id,
        impact_assessment_id=impact_assessment.id,
        score=decimal("78.4"),
        band=RiskBand.CRITICAL,
        model_version="1.0",
        explanation="High revenue exposure, constrained CPU supply, and fourteen at-risk orders.",
        calculated_at=SNAPSHOT_AT,
    )
    scenario_specs = (
        (
            "wait-and-monitor",
            "Wait and monitor",
            ScenarioStatus.FEASIBLE,
            "0",
            "14",
            "0",
            0,
            "0.95",
            "0.10",
        ),
        (
            "expedite-existing",
            "Expedite existing supply",
            ScenarioStatus.FEASIBLE,
            "240000",
            "5",
            "11200000",
            9,
            "0.81",
            "0.72",
        ),
        (
            "alternate-source",
            "Activate alternate source",
            ScenarioStatus.RECOMMENDED,
            "165000",
            "7",
            "15600000",
            12,
            "0.74",
            "0.89",
        ),
    )
    scenarios = tuple(
        Scenario(
            id=demo_id("scenario", key),
            organization_id=org_id,
            incident_id=incident.id,
            name=name,
            description=f"Mitigation option: {name.lower()}.",
            status=status,
            incremental_cost=decimal(cost),
            currency="INR",
            delay_days=decimal(delay),
            quantity_protected=decimal("280" if key != "wait-and-monitor" else "0"),
            orders_protected=orders,
            revenue_protected=decimal(revenue),
            expected_service_level=decimal("0.91" if key == "alternate-source" else "0.76"),
            feasibility_score=decimal(feasibility),
            objective_score=decimal(objective),
            assumptions=[{"statement": "Alternate supplier qualification remains valid"}],
            constraints=[{"name": "approved_budget", "limit": "300000 INR"}],
        )
        for (
            key,
            name,
            status,
            cost,
            delay,
            revenue,
            orders,
            feasibility,
            objective,
        ) in scenario_specs
    )
    scenario_by_key = {
        key: scenario
        for (key, *_remaining), scenario in zip(scenario_specs, scenarios, strict=True)
    }
    scenario_actions = tuple(
        ScenarioAction(
            id=demo_id("scenario-action", key),
            organization_id=org_id,
            scenario_id=scenario_by_key[key].id,
            sequence=1,
            action_type=action_type,
            parameters=parameters,
            incremental_cost=scenario_by_key[key].incremental_cost,
            expected_delay_days=scenario_by_key[key].delay_days,
            feasibility={"score": str(scenario_by_key[key].feasibility_score)},
        )
        for key, action_type, parameters in (
            ("wait-and-monitor", "MONITOR_SUPPLIER", {"interval_hours": 6}),
            ("expedite-existing", "EXPEDITE_SHIPMENT", {"mode": "AIR"}),
            ("alternate-source", "SWITCH_SUPPLIER", {"supplier_code": "HANSEONG"}),
        )
    )
    recommended_scenario = scenario_by_key["alternate-source"]
    recommendation = Recommendation(
        id=demo_id("recommendation", "taiwan-typhoon-2026"),
        organization_id=org_id,
        incident_id=incident.id,
        recommended_scenario_id=recommended_scenario.id,
        confidence=decimal("0.88"),
        rationale=(
            "The alternate source protects the most revenue within the approved budget and "
            "maintains a feasible seven-day recovery window."
        ),
        alternative_scenario_ids=[
            str(item.id) for item in scenarios if item.id != recommended_scenario.id
        ],
        assumptions=list(recommended_scenario.assumptions),
        risks=[
            {"risk": "Supplier onboarding lead time", "mitigation": "Use existing qualification"}
        ],
        structured_summary={
            "objective": "MAX_REVENUE_PROTECTED",
            "revenue_protected": "15600000",
            "incremental_cost": "165000",
            "expected_delay_days": "7",
        },
    )
    approval_request = ApprovalRequest(
        id=demo_id("approval-request", "taiwan-typhoon-2026"),
        organization_id=org_id,
        recommendation_id=recommendation.id,
        status=ApprovalStatus.PENDING,
        requested_by_user_id=user_by_email["manager@nova.example"].id,
        required_role_key=RoleKey.APPROVER.value,
        assigned_approver_user_id=user_by_email["approver@nova.example"].id,
        amount=decimal("165000"),
        currency="INR",
        due_at=SNAPSHOT_AT + timedelta(hours=8),
        policy_snapshot={"maximum_amount": "250000", "required_role": "APPROVER"},
    )
    execution_action = ExecutionAction(
        id=demo_id("execution-action", "taiwan-typhoon:alternate-source"),
        organization_id=org_id,
        recommendation_id=recommendation.id,
        scenario_action_id=next(
            action.id for action in scenario_actions if action.action_type == "SWITCH_SUPPLIER"
        ),
        action_type="SWITCH_SUPPLIER",
        adapter_key="mock.erp@1.0",
        idempotency_key="taiwan-typhoon-2026:switch-supplier",
        status=ExecutionStatus.PENDING,
        parameters={"supplier_code": "HANSEONG"},
        attempt_count=0,
    )
    audit_entry = AuditLog(
        id=demo_id("audit-log", "taiwan-typhoon:scenario-generated"),
        organization_id=org_id,
        occurred_at=SNAPSHOT_AT,
        actor_user_id=None,
        action="scenario.generated",
        entity_type="incident",
        entity_id=incident.id,
        workflow_version_id=workflow_version.id,
        request_id="seeded-taiwan-typhoon",
        before=None,
        after={"scenario_count": 3, "recommended": "alternate-source"},
        metadata_={"seeded": True},
    )

    suppliers = tuple(
        Supplier(
            id=demo_id("supplier", code),
            organization_id=org_id,
            code=code,
            name=name,
            legal_name=f"{name} Ltd.",
            country_code=country,
            criticality=criticality,
            metadata_={"demo": True, "scenario_ready": criticality >= 90},
        )
        for code, name, country, _city, criticality in SUPPLIER_SPECS
    )
    supplier_by_code = {supplier.code: supplier for supplier in suppliers}
    supplier_sites = tuple(
        SupplierSite(
            id=demo_id("supplier-site", f"{code}-01"),
            organization_id=org_id,
            supplier_id=supplier_by_code[code].id,
            code=f"{code}-01",
            name=f"{name} {city} Site",
            city=city,
            country_code=country,
            timezone="Asia/Kolkata" if country == "IN" else "UTC",
            capacity_metadata={"shift_pattern": "3x8", "demo": True},
            is_active=True,
        )
        for code, name, country, city, _criticality in SUPPLIER_SPECS
    )
    supplier_sites += (
        SupplierSite(
            id=demo_id("supplier-site", "FORMOSA-HSINCHU"),
            organization_id=org_id,
            supplier_id=supplier_by_code["FORMOSA"].id,
            code="FORMOSA-HSINCHU",
            name="Formosa Silicon Works Hsinchu Site",
            city="Hsinchu",
            country_code="TW",
            timezone="Asia/Taipei",
            capacity_metadata={"wafer_fab": True, "monthly_wafers": 42000},
            is_active=True,
        ),
    )
    site_by_supplier = {
        site.code.removesuffix("-01"): site for site in supplier_sites if site.code.endswith("-01")
    }

    supplier_ratings = tuple(
        SupplierRating(
            id=demo_id("supplier-rating", f"{code}:{rating_date.isoformat()}"),
            organization_id=org_id,
            supplier_id=supplier_by_code[code].id,
            rating_date=rating_date,
            overall_score=decimal(max(55, 94 - index * 2 - month_offset)),
            delivery_score=decimal(max(50, 92 - index - month_offset)),
            quality_score=decimal(max(60, 96 - index)),
            resilience_score=decimal(max(45, 88 - index * 2)),
            factors={"on_time_delivery": 0.93 - index * 0.01, "defect_ppm": 40 + index * 8},
            source="NOVA_SCORECARD",
        )
        for index, (code, *_rest) in enumerate(SUPPLIER_SPECS)
        for month_offset, rating_date in enumerate((date(2026, 7, 31), date(2026, 8, 31)))
    )

    materials = tuple(
        Material(
            id=demo_id("material", sku),
            organization_id=org_id,
            sku=sku,
            name=name,
            category=category,
            unit_of_measure="EA",
            criticality=criticality,
            standard_cost=decimal(cost),
            currency="INR",
            is_active=True,
        )
        for sku, name, category, cost, criticality, _suppliers in MATERIAL_SPECS
    )
    material_by_sku = {material.sku: material for material in materials}
    material_suppliers: list[MaterialSupplier] = []
    for material_index, (sku, _name, category, cost, _criticality, supplier_codes) in enumerate(
        MATERIAL_SPECS
    ):
        for supplier_index, supplier_code in enumerate(supplier_codes):
            country = supplier_by_code[supplier_code].country_code
            lead_time = 12 if country == "IN" else 28 + supplier_index * 7
            capacity_base = 18000 if category == "BATTERY" else 6500
            material_suppliers.append(
                MaterialSupplier(
                    id=demo_id("material-supplier", f"{sku}:{supplier_code}"),
                    organization_id=org_id,
                    material_id=material_by_sku[sku].id,
                    supplier_id=supplier_by_code[supplier_code].id,
                    supplier_site_id=site_by_supplier[supplier_code].id,
                    supplier_material_code=f"{supplier_code}-{sku}",
                    lead_time_days=lead_time,
                    minimum_order_quantity=decimal(100 if category == "SEMICONDUCTOR" else 250),
                    unit_cost=decimal(cost) * (decimal("1.00") + decimal("0.08") * supplier_index),
                    currency="INR",
                    monthly_capacity=decimal(capacity_base + material_index * 175),
                    allocated_capacity=decimal((capacity_base + material_index * 175) * 0.68),
                    is_primary=supplier_index == 0,
                    is_approved=True,
                )
            )

    products = tuple(
        Product(
            id=demo_id("product", sku),
            organization_id=org_id,
            sku=sku,
            name=name,
            category=category,
            unit_of_measure="EA",
            standard_price=decimal(price),
            currency="INR",
            is_active=True,
        )
        for sku, name, category, price in PRODUCT_SPECS
    )
    product_by_sku = {product.sku: product for product in products}

    facility_classes: dict[FacilityType, type[Facility]] = {
        FacilityType.PLANT: Plant,
        FacilityType.WAREHOUSE: Warehouse,
        FacilityType.DISTRIBUTION_CENTER: DistributionCenter,
    }
    facilities = tuple(
        facility_classes[facility_type](
            id=demo_id("facility", code),
            organization_id=org_id,
            code=code,
            name=name,
            facility_type=facility_type,
            city=city,
            region=region,
            country_code="IN",
            latitude=latitude,
            longitude=longitude,
            timezone="Asia/Kolkata",
            is_active=True,
        )
        for code, name, facility_type, city, region, latitude, longitude in FACILITY_SPECS
    )
    facility_by_code = {facility.code: facility for facility in facilities}

    customers = tuple(
        Customer(
            id=demo_id("customer", code),
            organization_id=org_id,
            code=code,
            name=name,
            priority=priority,
            country_code=country,
            segment=segment,
            annual_revenue=decimal(120000000 + index * 17500000),
            currency="INR",
        )
        for index, (code, name, priority, country, segment) in enumerate(CUSTOMER_SPECS)
    )

    bills_of_material = tuple(
        BillOfMaterial(
            id=demo_id("bom", product_code),
            organization_id=org_id,
            product_id=product_by_sku[product_code].id,
            version="1.0",
            effective_from=date(2026, 1, 1),
            is_active=True,
        )
        for product_code in BOM_SPECS
    )
    bom_by_product = {
        product_code: next(
            bom for bom in bills_of_material if bom.product_id == product_by_sku[product_code].id
        )
        for product_code in BOM_SPECS
    }
    bom_components: list[BOMComponent] = []
    for product_code, components in BOM_SPECS.items():
        for line_number, (
            entity_type,
            component_code,
            component_quantity,
            is_critical,
        ) in enumerate(components, start=1):
            bom_components.append(
                BOMComponent(
                    id=demo_id("bom-component", f"{product_code}:{line_number}"),
                    organization_id=org_id,
                    bill_of_material_id=bom_by_product[product_code].id,
                    line_number=line_number,
                    material_id=(
                        material_by_sku[component_code].id if entity_type == "material" else None
                    ),
                    component_product_id=(
                        product_by_sku[component_code].id if entity_type == "product" else None
                    ),
                    quantity=decimal(component_quantity),
                    unit_of_measure="EA",
                    scrap_factor=decimal("0.015") if entity_type == "material" else decimal("0"),
                    is_critical=is_critical,
                )
            )

    inventory_snapshots: list[InventorySnapshot] = []
    inventory_facilities = ("MUMBAI-WH", "HYD-WH", "PUNE-WH")
    plant_codes = ("PUNE-PLANT", "CHENNAI-PLANT", "BLR-PLANT")
    for material_index, material in enumerate(materials):
        material_facilities = inventory_facilities + (
            plant_codes[material_index % len(plant_codes)],
        )
        for facility_index, facility_code in enumerate(material_facilities):
            base_quantity = 900 + material_index * 115 + facility_index * 170
            if material.sku == "CPU-X9":
                base_quantity = (480, 320, 260, 190)[facility_index]
            elif material.sku == "PWR-IC-42":
                base_quantity = (1100, 760, 540, 380)[facility_index]
            elif material.sku == "CELL-LI6":
                base_quantity = (2100, 1250, 880, 620)[facility_index]
            inventory_snapshots.append(
                InventorySnapshot(
                    id=demo_id("inventory", f"{material.sku}:{facility_code}"),
                    organization_id=org_id,
                    facility_id=facility_by_code[facility_code].id,
                    material_id=material.id,
                    captured_at=SNAPSHOT_AT,
                    on_hand_quantity=decimal(base_quantity),
                    allocated_quantity=decimal(round(base_quantity * 0.22)),
                    in_transit_quantity=decimal(round(base_quantity * 0.15)),
                    safety_stock_quantity=decimal(round(base_quantity * 0.28)),
                    unit_of_measure="EA",
                    source_reference=f"ERP-INV-{material.sku}-{facility_code}",
                )
            )

    finished_product_codes = (
        "NOVABOOK-PRO",
        "NOVABOOK-AIR",
        "NOVASTATION-X1",
        "NOVAEDGE-GW",
    )
    product_inventory_facilities = ("MUMBAI-WH", "DELHI-DC", "CHENNAI-DC", "PUNE-WH")
    for product_index, product_code in enumerate(finished_product_codes):
        product = product_by_sku[product_code]
        for facility_index, facility_code in enumerate(product_inventory_facilities):
            base_quantity = 180 + product_index * 45 + facility_index * 35
            inventory_snapshots.append(
                InventorySnapshot(
                    id=demo_id("inventory", f"{product_code}:{facility_code}"),
                    organization_id=org_id,
                    facility_id=facility_by_code[facility_code].id,
                    product_id=product.id,
                    captured_at=SNAPSHOT_AT,
                    on_hand_quantity=decimal(base_quantity),
                    allocated_quantity=decimal(round(base_quantity * 0.35)),
                    in_transit_quantity=decimal(round(base_quantity * 0.12)),
                    safety_stock_quantity=decimal(round(base_quantity * 0.2)),
                    unit_of_measure="EA",
                    source_reference=f"ERP-INV-{product_code}-{facility_code}",
                )
            )

    consumption_history: list[ConsumptionHistory] = []
    for material_index, material in enumerate(materials):
        for plant_index, facility_code in enumerate(plant_codes):
            daily_use = 22 + material_index * 3 + plant_index * 5
            if material.sku == "CPU-X9":
                daily_use = (78, 54, 18)[plant_index]
            elif material.sku == "PWR-IC-42":
                daily_use = (155, 112, 48)[plant_index]
            elif material.sku == "CELL-LI6":
                daily_use = (340, 120, 20)[plant_index]
            consumption_history.append(
                ConsumptionHistory(
                    id=demo_id("consumption", f"{material.sku}:{facility_code}:2026-08"),
                    organization_id=org_id,
                    facility_id=facility_by_code[facility_code].id,
                    material_id=material.id,
                    period_start=date(2026, 8, 1),
                    period_end=date(2026, 8, 31),
                    quantity=decimal(daily_use * 31),
                    unit_of_measure="EA",
                    source_reference=f"ERP-CONS-{material.sku}-{facility_code}-202608",
                )
            )

    materials_by_primary_supplier: dict[str, list[str]] = defaultdict(list)
    material_cost_by_sku: dict[str, Decimal] = {}
    for sku, _name, _category, cost, _criticality, supplier_codes in MATERIAL_SPECS:
        materials_by_primary_supplier[supplier_codes[0]].append(sku)
        material_cost_by_sku[sku] = decimal(cost)
    po_supplier_codes = tuple(materials_by_primary_supplier)
    purchase_orders: list[PurchaseOrder] = []
    purchase_order_lines: list[PurchaseOrderLine] = []
    for po_index in range(30):
        supplier_code = po_supplier_codes[po_index % len(po_supplier_codes)]
        supplier_materials = materials_by_primary_supplier[supplier_code]
        selected_skus = tuple(
            supplier_materials[(po_index + line_offset) % len(supplier_materials)]
            for line_offset in range(min(2, len(supplier_materials)))
        )
        order_number = f"PO-2026-{1001 + po_index}"
        po_id = demo_id("purchase-order", order_number)
        order_date = date(2026, 8, 1) + timedelta(days=po_index % 25)
        quantities = tuple(
            decimal(650 + po_index * 35 + line * 125) for line in range(len(selected_skus))
        )
        total_amount = sum(
            (
                material_cost_by_sku[sku] * ordered_quantity
                for sku, ordered_quantity in zip(selected_skus, quantities, strict=True)
            ),
            start=decimal(0),
        )
        destination_code = (*plant_codes, "MUMBAI-WH", "HYD-WH")[po_index % 5]
        purchase_orders.append(
            PurchaseOrder(
                id=po_id,
                organization_id=org_id,
                order_number=order_number,
                supplier_id=supplier_by_code[supplier_code].id,
                supplier_site_id=site_by_supplier[supplier_code].id,
                destination_facility_id=facility_by_code[destination_code].id,
                status=(OrderStatus.PARTIALLY_FULFILLED if po_index % 7 == 0 else OrderStatus.OPEN),
                order_date=order_date,
                expected_delivery_date=order_date + timedelta(days=18 + po_index % 16),
                currency="INR",
                total_amount=total_amount,
                source_reference=f"NOVA-ERP-{order_number}",
                raw_payload={"seeded": True, "buyer_group": "GLOBAL_SOURCING"},
            )
        )
        for line_index, (sku, ordered_quantity) in enumerate(
            zip(selected_skus, quantities, strict=True), start=1
        ):
            purchase_order_lines.append(
                PurchaseOrderLine(
                    id=demo_id("purchase-order-line", f"{order_number}:{line_index}"),
                    organization_id=org_id,
                    purchase_order_id=po_id,
                    line_number=line_index,
                    material_id=material_by_sku[sku].id,
                    ordered_quantity=ordered_quantity,
                    received_quantity=(
                        ordered_quantity * decimal("0.35") if po_index % 7 == 0 else decimal(0)
                    ),
                    unit_of_measure="EA",
                    unit_price=material_cost_by_sku[sku],
                    expected_delivery_date=order_date + timedelta(days=18 + po_index % 16),
                    status=(
                        OrderStatus.PARTIALLY_FULFILLED if po_index % 7 == 0 else OrderStatus.OPEN
                    ),
                )
            )

    customer_by_code = {customer.code: customer for customer in customers}
    customer_orders: list[CustomerOrder] = []
    customer_order_lines: list[CustomerOrderLine] = []
    distribution_codes = ("DELHI-DC", "CHENNAI-DC", "MUMBAI-WH")
    for order_index in range(42):
        customer_code = CUSTOMER_SPECS[order_index % len(CUSTOMER_SPECS)][0]
        order_number = f"SO-2026-{5001 + order_index}"
        order_id = demo_id("customer-order", order_number)
        product_codes = (
            finished_product_codes[order_index % len(finished_product_codes)],
            finished_product_codes[(order_index + 1) % len(finished_product_codes)],
        )
        quantities = (decimal(12 + order_index * 2), decimal(7 + order_index))
        total_amount = sum(
            (
                (product_by_sku[product_code].standard_price or decimal(0)) * ordered_quantity
                for product_code, ordered_quantity in zip(product_codes, quantities, strict=True)
            ),
            start=decimal(0),
        )
        order_date = date(2026, 9, 1) + timedelta(days=order_index % 14)
        customer_orders.append(
            CustomerOrder(
                id=order_id,
                organization_id=org_id,
                order_number=order_number,
                customer_id=customer_by_code[customer_code].id,
                fulfillment_facility_id=facility_by_code[
                    distribution_codes[order_index % len(distribution_codes)]
                ].id,
                status=(
                    OrderStatus.PARTIALLY_FULFILLED if order_index % 9 == 0 else OrderStatus.OPEN
                ),
                order_date=order_date,
                requested_delivery_date=order_date + timedelta(days=12 + order_index % 8),
                currency="INR",
                total_amount=total_amount,
                source_reference=f"NOVA-CRM-{order_number}",
            )
        )
        for line_index, (product_code, ordered_quantity) in enumerate(
            zip(product_codes, quantities, strict=True), start=1
        ):
            price = product_by_sku[product_code].standard_price or decimal(0)
            customer_order_lines.append(
                CustomerOrderLine(
                    id=demo_id("customer-order-line", f"{order_number}:{line_index}"),
                    organization_id=org_id,
                    customer_order_id=order_id,
                    line_number=line_index,
                    product_id=product_by_sku[product_code].id,
                    ordered_quantity=ordered_quantity,
                    fulfilled_quantity=(
                        ordered_quantity * decimal("0.4") if order_index % 9 == 0 else decimal(0)
                    ),
                    unit_price=price,
                    promised_date=order_date + timedelta(days=12 + order_index % 8),
                )
            )

    po_lines_by_order: dict[UUID, list[PurchaseOrderLine]] = defaultdict(list)
    for line in purchase_order_lines:
        po_lines_by_order[line.purchase_order_id].append(line)
    shipments: list[Shipment] = []
    shipment_events: list[ShipmentEvent] = []
    for shipment_index, purchase_order in enumerate(purchase_orders[:20]):
        shipment_number = f"SHP-2026-{7001 + shipment_index}"
        shipment_id = demo_id("shipment", shipment_number)
        status = (
            ShipmentStatus.DELAYED if shipment_index in {2, 5, 8, 11} else ShipmentStatus.IN_TRANSIT
        )
        supplier_code = next(
            code
            for code, supplier in supplier_by_code.items()
            if supplier.id == purchase_order.supplier_id
        )
        contents = [
            {
                "material_id": str(line.material_id),
                "quantity": str(line.ordered_quantity),
                "unit": line.unit_of_measure,
            }
            for line in po_lines_by_order[purchase_order.id]
        ]
        departure = SNAPSHOT_AT - timedelta(days=9 - shipment_index % 6)
        shipments.append(
            Shipment(
                id=shipment_id,
                organization_id=org_id,
                shipment_number=shipment_number,
                purchase_order_id=purchase_order.id,
                supplier_id=purchase_order.supplier_id,
                origin_supplier_site_id=site_by_supplier[supplier_code].id,
                destination_facility_id=purchase_order.destination_facility_id,
                status=status,
                transportation_mode="OCEAN"
                if supplier_by_code[supplier_code].country_code != "IN"
                else "ROAD",
                carrier=("Maersk", "DHL Global Forwarding", "Blue Dart")[shipment_index % 3],
                tracking_reference=f"TRK-NOVA-{90001 + shipment_index}",
                departed_at=departure,
                estimated_arrival_at=SNAPSHOT_AT + timedelta(days=4 + shipment_index % 9),
                current_location=(
                    "Singapore Strait - delayed near port"
                    if status is ShipmentStatus.DELAYED
                    else "In transit to destination"
                ),
                contents=contents,
                source_reference=f"TMS-{shipment_number}",
            )
        )
        event_specs = (
            ("BOOKED", departure - timedelta(days=2), "Origin facility"),
            ("DEPARTED", departure, site_by_supplier[supplier_code].city),
            (
                "DELAY_REPORTED" if status is ShipmentStatus.DELAYED else "IN_TRANSIT",
                departure + timedelta(days=3),
                "Singapore" if supplier_by_code[supplier_code].country_code != "IN" else "India",
            ),
        )
        for event_index, (event_type, occurred_at, location) in enumerate(event_specs, start=1):
            shipment_events.append(
                ShipmentEvent(
                    id=demo_id("shipment-event", f"{shipment_number}:{event_index}"),
                    organization_id=org_id,
                    shipment_id=shipment_id,
                    source_event_id=f"{shipment_number}-EVT-{event_index}",
                    event_type=event_type,
                    occurred_at=occurred_at,
                    location=location,
                    description=f"{event_type.replace('_', ' ').title()} for {shipment_number}",
                    metadata_={"seeded": True},
                )
            )

    stages: tuple[tuple[EntityBase, ...], ...] = (
        (organization,),
        (
            *roles,
            *users,
            *connectors,
            *signal_sources,
            workflow_definition,
            *llm_configurations,
            *prompt_templates,
            *suppliers,
            *materials,
            *products,
            *facilities,
            *customers,
        ),
        (
            *user_roles,
            workflow_version,
            *supplier_sites,
            *supplier_ratings,
            *material_suppliers,
            *bills_of_material,
        ),
        (*workflow_stages,),
        (*workflow_configurations, *workflow_dependencies),
        (incident,),
        (impact_assessment, *scenarios),
        (*impact_metrics, risk_assessment, *scenario_actions),
        (recommendation,),
        (approval_request, execution_action),
        (audit_entry,),
        (
            *bom_components,
            *inventory_snapshots,
            *consumption_history,
            *purchase_orders,
            *customer_orders,
        ),
        (*purchase_order_lines, *customer_order_lines),
        tuple(shipments),
        tuple(shipment_events),
    )
    return DemoDataset(stages=stages)


async def _merge_stage(session: AsyncSession, entities: Iterable[EntityBase]) -> None:
    for entity in entities:
        await session.merge(entity)
    await session.flush()


async def _seed_in_session(session: AsyncSession) -> DemoSeedResult:
    existing_id = await session.scalar(
        select(Organization.id).where(Organization.slug == "nova-electronics")
    )
    dataset = build_demo_dataset(existing_id)
    for stage in dataset.stages:
        await _merge_stage(session, stage)
    return DemoSeedResult(
        organization_id=dataset.entities[0].id,
        counts=dataset.counts,
        total_entities=len(dataset.entities),
    )


async def seed_demo_data(session: AsyncSession | None = None) -> DemoSeedResult:
    """Insert or update the Nova dataset in one transaction."""

    if session is not None:
        return await _seed_in_session(session)

    async with async_session_factory() as owned_session, owned_session.begin():
        return await _seed_in_session(owned_session)
