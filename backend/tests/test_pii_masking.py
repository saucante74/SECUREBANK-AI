import pytest

from app.schemas.pii import PiiEntity
from app.services.pii import PiiDetector
from app.services.pii_masking import PiiMasker


class SimulatedDetector:
    def __init__(self, entities: list[PiiEntity]) -> None:
        self._entities = entities
        self.received_texts: list[str] = []

    def detect(self, text: str) -> list[PiiEntity]:
        self.received_texts.append(text)
        return self._entities


@pytest.fixture(scope="module")
def masker() -> PiiMasker:
    return PiiMasker(PiiDetector())


def entity(
    entity_type: str,
    start: int,
    end: int,
    score: float,
) -> PiiEntity:
    return PiiEntity(
        entity_type=entity_type,
        start=start,
        end=end,
        score=score,
    )


def test_masks_email(masker: PiiMasker) -> None:
    text = "Contact : alice.dupont@example.com."

    assert masker.mask(text) == "Contact : [EMAIL_ADDRESS]."


def test_masks_french_phone_number(masker: PiiMasker) -> None:
    text = "Téléphone : +33 6 12 34 56 78."

    assert masker.mask(text) == "Téléphone : [PHONE_NUMBER]."


def test_masks_valid_synthetic_iban(masker: PiiMasker) -> None:
    text = "IBAN fictif : CH93 0076 2011 6238 5295 7."

    assert masker.mask(text) == "IBAN fictif : [IBAN_CODE]."


def test_masks_person_name_detected_in_french(masker: PiiMasker) -> None:
    text = "La cliente fictive s'appelle Camille Martin."

    assert masker.mask(text) == "La cliente fictive s'appelle [PERSON]."


def test_masks_multiple_pii_types(masker: PiiMasker) -> None:
    text = (
        "Camille Martin utilise alice.dupont@example.com, +33 6 12 34 56 78 "
        "et CH93 0076 2011 6238 5295 7."
    )

    assert masker.mask(text) == (
        "[PERSON] utilise [EMAIL_ADDRESS], [PHONE_NUMBER] et [IBAN_CODE]."
    )


def test_returns_text_without_pii_unchanged(masker: PiiMasker) -> None:
    text = "Le contrôle synthétique est terminé."

    assert masker.mask(text) == text


def test_returns_empty_text(masker: PiiMasker) -> None:
    assert masker.mask("") == ""


def test_preserves_non_sensitive_text_accents_and_punctuation(
    masker: PiiMasker,
) -> None:
    text = "Écrivez à alice.dupont@example.com, dès aujourd'hui !"

    assert masker.mask(text) == "Écrivez à [EMAIL_ADDRESS], dès aujourd'hui !"


def test_uses_original_positions_for_multiple_replacements() -> None:
    text = "Avant alpha milieu beta après"
    detector = SimulatedDetector(
        [
            entity("EMAIL_ADDRESS", 6, 11, 0.8),
            entity("IBAN_CODE", 19, 23, 0.9),
        ]
    )

    assert PiiMasker(detector).mask(text) == (
        "Avant [EMAIL_ADDRESS] milieu [IBAN_CODE] après"
    )
    assert detector.received_texts == [text]


def test_overlap_prefers_highest_score() -> None:
    text = "abcdefghij"
    detector = SimulatedDetector(
        [
            entity("PERSON", 0, 8, 0.7),
            entity("EMAIL_ADDRESS", 2, 6, 0.9),
        ]
    )

    assert PiiMasker(detector).mask(text) == "ab[EMAIL_ADDRESS]ghij"


def test_equal_score_overlap_prefers_longest_entity() -> None:
    text = "abcdefghij"
    detector = SimulatedDetector(
        [
            entity("EMAIL_ADDRESS", 2, 6, 0.8),
            entity("PERSON", 0, 8, 0.8),
        ]
    )

    assert PiiMasker(detector).mask(text) == "[PERSON]ij"


def test_exact_overlap_tie_is_deterministic() -> None:
    text = "abcdefghij"
    first_order = SimulatedDetector(
        [
            entity("PERSON", 2, 6, 0.8),
            entity("EMAIL_ADDRESS", 2, 6, 0.8),
        ]
    )
    reversed_order = SimulatedDetector(
        [
            entity("EMAIL_ADDRESS", 2, 6, 0.8),
            entity("PERSON", 2, 6, 0.8),
        ]
    )

    expected = "ab[EMAIL_ADDRESS]ghij"
    assert PiiMasker(first_order).mask(text) == expected
    assert PiiMasker(reversed_order).mask(text) == expected
