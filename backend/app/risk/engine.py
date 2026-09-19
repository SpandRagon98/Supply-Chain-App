"""Transparent weighted risk scoring independent of transport or AI layers."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import RiskBand, Severity

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "severity": Decimal("0.25"),
    "confidence": Decimal("0.10"),
    "supplier_criticality": Decimal("0.20"),
    "single_source_dependency": Decimal("0.20"),
    "inventory_exposure": Decimal("0.15"),
    "revenue_exposure": Decimal("0.10"),
}


@dataclass(frozen=True, slots=True)
class RiskScoringConfig:
    weights: Mapping[str, Decimal]
    revenue_reference: Decimal = Decimal("10000000")
    inventory_days_threshold: Decimal = Decimal("14")
    model_version: str = "risk-v1"

    @classmethod
    def default(cls) -> "RiskScoringConfig":
        return cls(DEFAULT_WEIGHTS)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "RiskScoringConfig":
        weights = {
            key: Decimal(str(value))
            for key, value in dict(data.get("weights", DEFAULT_WEIGHTS)).items()
        }
        config = cls(
            weights,
            Decimal(str(data.get("revenue_reference", "10000000"))),
            Decimal(str(data.get("inventory_days_threshold", "14"))),
            str(data.get("model_version", "risk-v1")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if set(self.weights) != set(DEFAULT_WEIGHTS):
            raise ValueError("Risk weights must define every supported factor exactly once")
        if any(value < 0 for value in self.weights.values()) or sum(
            self.weights.values()
        ) != Decimal(1):
            raise ValueError("Risk factor weights must be non-negative and sum exactly to 1")
        if self.revenue_reference <= 0 or self.inventory_days_threshold <= 0:
            raise ValueError("Risk reference values must be positive")


@dataclass(frozen=True, slots=True)
class RiskFactorValue:
    key: str
    raw_value: Decimal
    normalized_value: Decimal
    weight: Decimal
    contribution: Decimal
    lineage: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class RiskResult:
    score: Decimal
    band: RiskBand
    factors: tuple[RiskFactorValue, ...]
    explanation: str


class RiskEngine:
    def score(
        self,
        incident: object,
        impact_summary: Mapping[str, object],
        impact_metrics: Mapping[str, Decimal],
        material_suppliers: tuple[object, ...],
        suppliers: tuple[object, ...],
        config: RiskScoringConfig | None = None,
    ) -> RiskResult:
        config = config or RiskScoringConfig.default()
        config.validate()
        severity_values = {
            Severity.INFORMATIONAL: Decimal(0),
            Severity.LOW: Decimal(".25"),
            Severity.MEDIUM: Decimal(".5"),
            Severity.HIGH: Decimal(".75"),
            Severity.CRITICAL: Decimal(1),
        }
        affected_materials = {
            str(value) for value in impact_summary.get("affected_material_ids", [])
        }
        supplier_by_id = {supplier.id: supplier for supplier in suppliers}
        impacted_links = [
            link
            for link in material_suppliers
            if str(link.material_id) in affected_materials
        ]
        affected_supplier_ids = {link.supplier_id for link in impacted_links}
        criticalities = [
            Decimal(supplier_by_id[value].criticality)
            for value in affected_supplier_ids
            if value in supplier_by_id
        ]
        source_counts: dict[str, int] = {}
        for link in material_suppliers:
            source_counts[str(link.material_id)] = (
                source_counts.get(str(link.material_id), 0) + 1
            )
        single_source = sum(source_counts.get(material, 0) <= 1 for material in affected_materials)
        coverage = impact_summary.get("inventory_coverage", [])
        days = [
            Decimal(str(row["days_of_supply"]))
            for row in coverage
            if isinstance(row, Mapping) and row.get("days_of_supply") is not None
        ]
        raw: dict[str, tuple[Decimal, Decimal, tuple[dict[str, object], ...]]] = {
            "severity": (
                severity_values[incident.severity],
                severity_values[incident.severity],
                ({"incident_id": str(incident.id)},),
            ),
            "confidence": (
                Decimal(incident.confidence),
                min(max(Decimal(incident.confidence), Decimal(0)), Decimal(1)),
                (),
            ),
            "supplier_criticality": (
                (max(criticalities) if criticalities else Decimal(0)),
                (max(criticalities) / Decimal(100) if criticalities else Decimal(0)),
                tuple(
                    {
                        "supplier_id": str(value),
                        "criticality": str(supplier_by_id[value].criticality),
                    }
                    for value in affected_supplier_ids
                    if value in supplier_by_id
                ),
            ),
            "single_source_dependency": (
                Decimal(single_source),
                Decimal(single_source) / Decimal(max(len(affected_materials), 1)),
                tuple(
                    {"material_id": material, "source_count": source_counts.get(material, 0)}
                    for material in affected_materials
                ),
            ),
            "inventory_exposure": (
                (min(days) if days else config.inventory_days_threshold),
                max(
                    Decimal(0),
                    Decimal(1)
                    - min(days, default=config.inventory_days_threshold)
                    / config.inventory_days_threshold,
                ),
                tuple({"days_of_supply": str(value)} for value in days),
            ),
            "revenue_exposure": (
                impact_metrics.get("revenue_at_risk", Decimal(0)),
                min(
                    impact_metrics.get("revenue_at_risk", Decimal(0)) / config.revenue_reference,
                    Decimal(1),
                ),
                (),
            ),
        }
        factors = tuple(
            RiskFactorValue(
                key,
                raw_value,
                normalized,
                config.weights[key],
                (normalized * config.weights[key] * Decimal(100)).quantize(
                    Decimal(".0001"), rounding=ROUND_HALF_UP
                ),
                lineage,
            )
            for key, (raw_value, normalized, lineage) in raw.items()
        )
        score = sum((factor.contribution for factor in factors), Decimal(0)).quantize(
            Decimal(".001"), rounding=ROUND_HALF_UP
        )
        band = (
            RiskBand.CRITICAL
            if score >= 80
            else RiskBand.HIGH
            if score >= 60
            else RiskBand.MEDIUM
            if score >= 35
            else RiskBand.LOW
        )
        leaders = ", ".join(
            factor.key
            for factor in sorted(factors, key=lambda item: item.contribution, reverse=True)[:2]
        )
        return RiskResult(
            score, band, factors, f"{band.value} risk ({score}/100), led by {leaders}."
        )
