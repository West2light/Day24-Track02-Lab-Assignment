# src/pii/detector.py
from dataclasses import dataclass
import re


NAME_PATTERN = r"\b[^\W\d_]+(?:[\s-]+[^\W\d_]+){1,4}\b"
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
CCCD_PATTERN = r"(?<!\d)\d{12}(?!\d)"
VN_PHONE_PATTERN = r"(?<!\d)0[35789]\d{8}(?!\d)"


@dataclass
class RecognizerResult:
    entity_type: str
    start: int
    end: int
    score: float


class RegexVietnameseAnalyzer:
    """
    Lightweight analyzer used for the lab and as a fallback when Presidio's
    spaCy stack is unavailable in the local environment.
    """

    PATTERNS = {
        "VN_CCCD": re.compile(CCCD_PATTERN),
        "VN_PHONE": re.compile(VN_PHONE_PATTERN),
        "EMAIL_ADDRESS": re.compile(EMAIL_PATTERN),
        "PERSON": re.compile(NAME_PATTERN),
    }

    def analyze(self, text: str, language: str = "vi", entities: list | None = None):
        del language
        text = str(text).strip()
        requested_entities = entities or list(self.PATTERNS)
        results = []

        for entity_type in requested_entities:
            pattern = self.PATTERNS.get(entity_type)
            if pattern is None:
                continue

            score = 0.7 if entity_type == "PERSON" else 0.9
            for match in pattern.finditer(text):
                results.append(
                    RecognizerResult(
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        score=score,
                    )
                )

        if "PERSON" in requested_entities:
            results.extend(self._detect_full_name(text))

        return self._deduplicate(results)

    @staticmethod
    def _detect_full_name(text: str) -> list[RecognizerResult]:
        """
        Treat a whole string as a person name when it looks like a standalone
        Vietnamese full name: 2-5 tokens, no digits, no email marker.
        """
        if not text or "@" in text or re.search(r"\d", text):
            return []

        normalized = " ".join(text.split())
        tokens = normalized.split(" ")
        if 2 <= len(tokens) <= 5 and all(re.fullmatch(r"[^\W\d_]+", token) for token in tokens):
            return [
                RecognizerResult(
                    entity_type="PERSON",
                    start=0,
                    end=len(normalized),
                    score=0.9,
                )
            ]

        return []

    @staticmethod
    def _deduplicate(results: list[RecognizerResult]) -> list[RecognizerResult]:
        unique = {}
        for result in results:
            key = (result.entity_type, result.start, result.end)
            if key not in unique or result.score > unique[key].score:
                unique[key] = result
        return sorted(unique.values(), key=lambda item: (item.start, item.end))


def _build_presidio_analyzer():
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        supported_language="vi",
        patterns=[Pattern(name="cccd_pattern", regex=CCCD_PATTERN, score=0.9)],
        context=["cccd", "can cuoc", "chung minh", "cmnd"],
    )

    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        supported_language="vi",
        patterns=[Pattern(name="vn_phone", regex=VN_PHONE_PATTERN, score=0.85)],
        context=["dien thoai", "sdt", "phone", "lien he"],
    )

    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        supported_language="vi",
        patterns=[Pattern(name="email_pattern", regex=EMAIL_PATTERN, score=0.85)],
        context=["email", "mail"],
    )

    person_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        supported_language="vi",
        patterns=[Pattern(name="name_pattern", regex=NAME_PATTERN, score=0.75)],
        context=["benh nhan", "ho ten", "bac si", "ten"],
    )

    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "vi", "model_name": "vi_core_news_lg"}],
        }
    )
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["vi"])
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(email_recognizer)
    analyzer.registry.add_recognizer(person_recognizer)
    return analyzer


def build_vietnamese_analyzer():
    """
    Prefer Presidio when its dependencies are healthy; otherwise use the local
    regex analyzer so the lab can still run.
    """
    try:
        return _build_presidio_analyzer()
    except Exception:
        return RegexVietnameseAnalyzer()


def detect_pii(text: str, analyzer) -> list:
    """
    Detect PII in Vietnamese text.
    """
    text = str(text)
    entities = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]

    primary_results = analyzer.analyze(
        text=text,
        language="vi",
        entities=entities,
    )

    fallback_results = RegexVietnameseAnalyzer().analyze(
        text=text,
        language="vi",
        entities=entities,
    )

    normalized_results = []
    for result in primary_results:
        if isinstance(result, RecognizerResult):
            normalized_results.append(result)
        else:
            normalized_results.append(
                RecognizerResult(
                    entity_type=result.entity_type,
                    start=result.start,
                    end=result.end,
                    score=result.score,
                )
            )

    combined_results = normalized_results + fallback_results
    return RegexVietnameseAnalyzer._deduplicate(combined_results)
