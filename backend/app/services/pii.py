import tldextract
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import EmailRecognizer

from app.schemas.pii import PiiEntity

SUPPORTED_ENTITIES = (
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "PERSON",
)


class LocalEmailRecognizer(EmailRecognizer):
    def __init__(self) -> None:
        super().__init__(supported_language="fr")
        self._domain_extractor = tldextract.TLDExtract(
            cache_dir=None,
            suffix_list_urls=(),
        )

    def validate_result(self, pattern_text: str) -> bool:
        return self._domain_extractor(pattern_text).fqdn != ""


class PiiDetector:
    def __init__(self) -> None:
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "fr", "model_name": "fr_core_news_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        analyzer = AnalyzerEngine(
            nlp_engine=provider.create_engine(),
            supported_languages=["fr"],
        )
        registry = analyzer.registry
        if registry is None:
            raise RuntimeError("Presidio recognizer registry is unavailable")
        registry.remove_recognizer("EmailRecognizer")
        registry.add_recognizer(LocalEmailRecognizer())
        self._analyzer = analyzer

    def detect(self, text: str) -> list[PiiEntity]:
        if not text:
            return []

        results = self._analyzer.analyze(
            text=text,
            language="fr",
            entities=list(SUPPORTED_ENTITIES),
        )
        return [
            PiiEntity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
            )
            for result in results
        ]
