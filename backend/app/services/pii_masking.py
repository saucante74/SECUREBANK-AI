from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

from app.schemas.pii import PiiEntity
from app.services.pii import PiiDetector

PII_MARKERS: Mapping[str, str] = MappingProxyType(
    {
        "EMAIL_ADDRESS": "[EMAIL_ADDRESS]",
        "PHONE_NUMBER": "[PHONE_NUMBER]",
        "IBAN_CODE": "[IBAN_CODE]",
        "PERSON": "[PERSON]",
    }
)


class PiiDetectionService(Protocol):
    def detect(self, text: str) -> list[PiiEntity]: ...


class PiiMaskingError(RuntimeError):
    pass


class PiiMasker:
    def __init__(self, detector: PiiDetectionService | None = None) -> None:
        self._detector = detector if detector is not None else PiiDetector()

    def mask(self, text: str) -> str:
        if not text:
            return ""

        try:
            detected_entities = self._detector.detect(text)
        except (OSError, RuntimeError) as error:
            raise PiiMaskingError("PII detection is unavailable") from error
        entities = self._resolve_overlaps(
            self._validate_entities(text, detected_entities)
        )
        masked_parts: list[str] = []
        cursor = 0

        for entity in entities:
            masked_parts.append(text[cursor : entity.start])
            masked_parts.append(PII_MARKERS[entity.entity_type])
            cursor = entity.end

        masked_parts.append(text[cursor:])
        return "".join(masked_parts)

    @staticmethod
    def _validate_entities(text: str, entities: object) -> list[PiiEntity]:
        if not isinstance(entities, list):
            raise PiiMaskingError("PII detection returned an invalid result")
        for entity in entities:
            if (
                not isinstance(entity, PiiEntity)
                or entity.entity_type not in PII_MARKERS
                or entity.start >= entity.end
                or entity.end > len(text)
            ):
                raise PiiMaskingError("PII detection returned an invalid result")
        return entities

    @staticmethod
    def _resolve_overlaps(entities: list[PiiEntity]) -> list[PiiEntity]:
        ranked_entities = sorted(
            entities,
            key=lambda entity: (
                -entity.score,
                -(entity.end - entity.start),
                entity.start,
                entity.end,
                entity.entity_type,
            ),
        )
        selected_entities: list[PiiEntity] = []

        for candidate in ranked_entities:
            overlaps = any(
                candidate.start < selected.end and selected.start < candidate.end
                for selected in selected_entities
            )
            if not overlaps:
                selected_entities.append(candidate)

        return sorted(
            selected_entities,
            key=lambda entity: (entity.start, entity.end, entity.entity_type),
        )
