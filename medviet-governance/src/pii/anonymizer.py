# src/pii/anonymizer.py
from hashlib import sha256
import random

import pandas as pd
from faker import Faker

from .detector import RecognizerResult, build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


def fake_cccd() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(12))


def fake_vn_phone() -> str:
    return f"0{random.choice(['3', '5', '7', '8', '9'])}" + "".join(
        str(random.randint(0, 9)) for _ in range(8)
    )


def mask_value(value: str, chars_to_mask: int = 8) -> str:
    value = str(value)
    visible = max(len(value) - chars_to_mask, 0)
    return ("*" * min(chars_to_mask, len(value))) + value[-visible:]


class MedVietAnonymizer:
    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self._presidio_anonymizer = self._build_presidio_anonymizer()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """
        Anonymize text using replace, mask, or hash strategy.
        """
        text = str(text)
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        if self._presidio_anonymizer is not None:
            return self._anonymize_with_presidio(text, results, strategy)

        replacements = []
        for result in results:
            original = text[result.start : result.end]
            replacements.append(
                (result.start, result.end, self._replacement_for(result, original, strategy))
            )

        return self._apply_replacements(text, replacements)

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Anonymize the lab dataframe while preserving model-training columns.
        """
        df_anon = df.copy()

        if "ho_ten" in df_anon.columns:
            df_anon["ho_ten"] = [fake.name() for _ in range(len(df_anon))]

        if "cccd" in df_anon.columns:
            df_anon["cccd"] = [fake_cccd() for _ in range(len(df_anon))]

        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = [
                fake_vn_phone() for _ in range(len(df_anon))
            ]

        if "email" in df_anon.columns:
            df_anon["email"] = [fake.email() for _ in range(len(df_anon))]

        if "dia_chi" in df_anon.columns:
            df_anon["dia_chi"] = [fake.address() for _ in range(len(df_anon))]

        if "ngay_sinh" in df_anon.columns:
            df_anon["ngay_sinh"] = df_anon["ngay_sinh"].apply(
                self.generalize_birth_date
            )

        if "bac_si_phu_trach" in df_anon.columns:
            df_anon["bac_si_phu_trach"] = [
                fake.name() for _ in range(len(df_anon))
            ]

        return df_anon

    def calculate_detection_rate(
        self,
        original_df: pd.DataFrame,
        pii_columns: list,
    ) -> float:
        """
        Calculate the percentage of PII cells detected successfully.
        """
        total = 0
        detected = 0

        for col in pii_columns:
            if col not in original_df.columns:
                continue

            for value in original_df[col].astype(str):
                total += 1
                normalized_value = self._normalize_for_detection(col, value)
                results = detect_pii(normalized_value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0

    @staticmethod
    def generalize_birth_date(value: str) -> str:
        """
        Convert a date of birth to a coarser birth year.
        """
        value = str(value)
        year = value[-4:] if len(value) >= 4 else value
        return f"YEAR_{year}"

    def _replacement_for(
        self,
        result: RecognizerResult,
        original: str,
        strategy: str,
    ) -> str:
        if strategy == "replace":
            return self._fake_value_for_entity(result.entity_type)
        if strategy == "mask":
            return mask_value(original)
        if strategy == "hash":
            return sha256(original.encode("utf-8")).hexdigest()
        raise ValueError(f"Unsupported anonymization strategy: {strategy}")

    @staticmethod
    def _apply_replacements(text: str, replacements: list[tuple[int, int, str]]) -> str:
        updated = text
        for start, end, replacement in sorted(replacements, reverse=True):
            updated = updated[:start] + replacement + updated[end:]
        return updated

    @staticmethod
    def _fake_value_for_entity(entity_type: str) -> str:
        if entity_type == "PERSON":
            return fake.name()
        if entity_type == "EMAIL_ADDRESS":
            return fake.email()
        if entity_type == "VN_CCCD":
            return fake_cccd()
        if entity_type == "VN_PHONE":
            return fake_vn_phone()
        return "[REDACTED]"

    @staticmethod
    def _normalize_for_detection(column_name: str, value: str) -> str:
        text = str(value).strip()
        digits_only = "".join(ch for ch in text if ch.isdigit())

        if column_name == "so_dien_thoai" and digits_only:
            if len(digits_only) == 9:
                return f"0{digits_only}"
            return digits_only

        if column_name == "cccd" and digits_only:
            if len(digits_only) < 12:
                return digits_only.zfill(12)
            return digits_only

        return text

    @staticmethod
    def _build_presidio_anonymizer():
        try:
            from presidio_anonymizer import AnonymizerEngine

            return AnonymizerEngine()
        except Exception:
            return None

    def _anonymize_with_presidio(self, text: str, results: list, strategy: str) -> str:
        from presidio_anonymizer.entities import OperatorConfig

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig("replace", {"new_value": fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", {"new_value": fake_vn_phone()}),
            }
        elif strategy == "mask":
            operators = {
                "DEFAULT": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 8,
                        "from_end": False,
                    },
                )
            }
        elif strategy == "hash":
            operators = {"DEFAULT": OperatorConfig("hash", {"hash_type": "sha256"})}
        else:
            raise ValueError(f"Unsupported anonymization strategy: {strategy}")

        presidio_results = [
            result
            if hasattr(result, "analysis_explanation")
            else self._to_presidio_result(result)
            for result in results
        ]
        anonymized = self._presidio_anonymizer.anonymize(
            text=text,
            analyzer_results=presidio_results,
            operators=operators,
        )
        return anonymized.text

    @staticmethod
    def _to_presidio_result(result: RecognizerResult):
        from presidio_analyzer import RecognizerResult as PresidioRecognizerResult

        return PresidioRecognizerResult(
            entity_type=result.entity_type,
            start=result.start,
            end=result.end,
            score=result.score,
        )
