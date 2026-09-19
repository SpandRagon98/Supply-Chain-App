"""Deterministic exact and fuzzy entity resolution."""

import re
from decimal import Decimal
from difflib import SequenceMatcher

from app.intelligence.contracts import (
    EntityCandidate,
    EntityMatch,
    EntityReference,
    SignalIntelligenceConfig,
)


def _match_text(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


class EntityResolver:
    def resolve(
        self,
        references: tuple[EntityReference, ...],
        candidates: tuple[EntityCandidate, ...],
        config: SignalIntelligenceConfig,
    ) -> tuple[EntityMatch, ...]:
        matches: dict[tuple[str, object], EntityMatch] = {}
        for reference in references:
            scored = self._score_reference(reference, candidates)
            eligible = [item for item in scored if item[0] >= config.entity_match_threshold]
            if not eligible:
                continue
            best_score = max(score for score, _method, _candidate in eligible)
            for score, method, candidate in eligible:
                if score != best_score:
                    continue
                match = EntityMatch(
                    entity_type=candidate.entity_type,
                    entity_id=candidate.entity_id,
                    confidence=score,
                    method=method,
                    requires_review=score < config.entity_review_threshold,
                    reference=reference,
                )
                identity = (match.entity_type, match.entity_id)
                current = matches.get(identity)
                if current is None or match.confidence > current.confidence:
                    matches[identity] = match
        return tuple(
            sorted(matches.values(), key=lambda item: (item.entity_type, str(item.entity_id)))
        )

    @staticmethod
    def _score_reference(
        reference: EntityReference,
        candidates: tuple[EntityCandidate, ...],
    ) -> list[tuple[Decimal, str, EntityCandidate]]:
        expected = _match_text(reference.value)
        scored: list[tuple[Decimal, str, EntityCandidate]] = []
        for candidate in candidates:
            if candidate.entity_type != reference.entity_type:
                continue
            best_score = Decimal("0")
            best_method = "NO_MATCH"
            for field_name, alias in candidate.aliases:
                actual = _match_text(alias)
                if actual == expected:
                    score = Decimal("1") if field_name == reference.field else Decimal("0.93")
                    method = f"EXACT_{field_name.upper()}"
                else:
                    ratio = Decimal(str(round(SequenceMatcher(None, expected, actual).ratio(), 5)))
                    multiplier = (
                        Decimal("0.90") if field_name == reference.field else Decimal("0.85")
                    )
                    score = ratio * multiplier
                    method = f"FUZZY_{field_name.upper()}"
                if score > best_score:
                    best_score = score
                    best_method = method
            scored.append((best_score, best_method, candidate))
        return scored
