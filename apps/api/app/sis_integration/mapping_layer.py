"""Curriculum and entity mapping layer for translating external SIS identifiers to canonical entities."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from .errors import MappingAmbiguousError, MappingMissingError
from .models import UniversityMapping

EntityType = Literal["FACULTY", "MAJOR", "PLAN", "COURSE", "TERM", "SECTION"]


class MappingLayer:
    """In-memory or repository-backed mapping service for a university tenant."""

    def __init__(
        self,
        university_id: UUID,
        mappings: list[UniversityMapping] | None = None,
    ) -> None:
        self.university_id = university_id
        # Key: (entity_type, external_code.upper()) -> UniversityMapping
        self._by_external: dict[tuple[str, str], UniversityMapping] = {}
        # Key: (entity_type, canonical_code.upper()) -> list[UniversityMapping]
        self._by_canonical: dict[tuple[str, str], list[UniversityMapping]] = {}
        if mappings:
            for m in mappings:
                self.add_mapping(m)

    def add_mapping(self, mapping: UniversityMapping) -> None:
        ext_key = (mapping.entity_type, mapping.external_code.strip().upper())
        self._by_external[ext_key] = mapping

        can_key_val = (mapping.canonical_code or mapping.canonical_id).strip().upper()
        can_key = (mapping.entity_type, can_key_val)
        self._by_canonical.setdefault(can_key, []).append(mapping)

    def resolve_external(
        self,
        entity_type: EntityType,
        external_code: str,
        *,
        required: bool = True,
    ) -> UniversityMapping | None:
        """Resolve external code to canonical mapping."""
        key = (entity_type, external_code.strip().upper())
        mapping = self._by_external.get(key)
        if not mapping and required:
            raise MappingMissingError(
                f"Missing required {entity_type} mapping for external code '{external_code}' (tenant: {self.university_id})"
            )
        return mapping

    def resolve_canonical(
        self,
        entity_type: EntityType,
        canonical_code: str,
        *,
        required: bool = True,
    ) -> UniversityMapping | None:
        """Reverse lookup: resolve canonical code to external mapping."""
        key = (entity_type, canonical_code.strip().upper())
        matches = self._by_canonical.get(key, [])
        if not matches:
            if required:
                raise MappingMissingError(
                    f"No external mapping found for canonical {entity_type} '{canonical_code}'"
                )
            return None
        if len(matches) > 1:
            raise MappingAmbiguousError(
                f"Multiple external codes map to canonical {entity_type} '{canonical_code}'"
            )
        return matches[0]

    def compute_coverage(
        self,
        known_external_entities: dict[EntityType, list[str]],
    ) -> dict[str, float]:
        """Compute coverage percentages per entity type and overall."""
        coverage: dict[str, float] = {}
        total_known = 0
        total_mapped = 0

        for raw_type, codes in known_external_entities.items():
            norm_type = str(raw_type).strip().upper()
            if not codes:
                coverage[norm_type.lower()] = 100.0
                coverage[norm_type] = 100.0
                continue
            mapped_count = sum(
                1 for c in codes if (norm_type, c.strip().upper()) in self._by_external
            )
            pct = round((mapped_count / len(codes)) * 100.0, 1)
            coverage[norm_type.lower()] = pct
            coverage[norm_type] = pct
            total_known += len(codes)
            total_mapped += mapped_count

        overall = round((total_mapped / total_known) * 100.0, 1) if total_known > 0 else 100.0
        coverage["overall"] = overall
        return coverage

    def list_unmapped(
        self,
        entity_type: EntityType,
        external_codes: list[str],
    ) -> list[str]:
        """Identify which external codes lack a canonical mapping."""
        return [
            code for code in external_codes
            if (entity_type, code.strip().upper()) not in self._by_external
        ]
