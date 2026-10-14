import pytest

from app.schemas.pii import PiiEntity
from app.services.pii import PiiDetector


@pytest.fixture(scope="module")
def detector() -> PiiDetector:
    return PiiDetector()


def entities_of_type(entities: list[PiiEntity], entity_type: str) -> list[PiiEntity]:
    return [entity for entity in entities if entity.entity_type == entity_type]


def test_detects_email_with_exact_position(detector: PiiDetector) -> None:
    email = "alice.dupont@example.com"
    text = f"Contact fictif : {email}"

    entities = entities_of_type(detector.detect(text), "EMAIL_ADDRESS")

    assert len(entities) == 1
    assert entities[0].start == text.index(email)
    assert entities[0].end == text.index(email) + len(email)
    assert text[entities[0].start : entities[0].end] == email


def test_detects_french_phone_number(detector: PiiDetector) -> None:
    entities = entities_of_type(
        detector.detect("Téléphone fictif : +33 6 12 34 56 78"),
        "PHONE_NUMBER",
    )

    assert len(entities) == 1


def test_detects_valid_synthetic_iban(detector: PiiDetector) -> None:
    entities = entities_of_type(
        detector.detect("IBAN de test : CH93 0076 2011 6238 5295 7"),
        "IBAN_CODE",
    )

    assert len(entities) == 1


def test_detects_multiple_pii_types(detector: PiiDetector) -> None:
    text = (
        "Le dossier fictif de Camille Martin contient alice.dupont@example.com, "
        "+33 6 12 34 56 78 et CH93 0076 2011 6238 5295 7."
    )

    entity_types = {entity.entity_type for entity in detector.detect(text)}

    assert {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE"} <= entity_types


def test_returns_no_entity_for_text_without_pii(detector: PiiDetector) -> None:
    assert detector.detect("Le contrôle synthétique est terminé.") == []


def test_returns_no_entity_for_empty_text(detector: PiiDetector) -> None:
    assert detector.detect("") == []


def test_returns_normalized_confidence_scores(detector: PiiDetector) -> None:
    entities = detector.detect("Contact fictif : alice.dupont@example.com")

    assert entities
    assert all(0.0 <= entity.score <= 1.0 for entity in entities)
    assert all(entity.score > 0.0 for entity in entities)


def test_detects_person_name_in_french_context(detector: PiiDetector) -> None:
    name = "Camille Martin"
    text = f"La cliente fictive s'appelle {name}."

    entities = entities_of_type(detector.detect(text), "PERSON")

    assert any(text[entity.start : entity.end] == name for entity in entities)
