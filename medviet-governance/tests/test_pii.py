# tests/test_pii.py
import pandas as pd
import pytest

from src.pii.anonymizer import MedVietAnonymizer


@pytest.fixture
def anonymizer():
    return MedVietAnonymizer()


@pytest.fixture
def sample_df():
    return pd.read_csv("data/raw/patients_raw.csv").head(50)


class TestPIIDetection:
    def test_cccd_detected(self, anonymizer):
        text = "Benh nhan Nguyen Van A, CCCD: 012345678901"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["VN_CCCD"],
        )
        assert len(results) >= 1

    def test_phone_detected(self, anonymizer):
        text = "Lien he: 0912345678"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["VN_PHONE"],
        )
        assert len(results) >= 1

    def test_email_detected(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["EMAIL_ADDRESS"],
        )
        assert len(results) >= 1

    def test_detection_rate_above_95_percent(self, anonymizer, sample_df):
        """Pipeline must reach at least 95% detection rate."""
        pii_columns = ["ho_ten", "cccd", "so_dien_thoai", "email"]
        rate = anonymizer.calculate_detection_rate(sample_df, pii_columns)
        print(f"\nDetection rate: {rate:.2%}")
        assert rate >= 0.95, f"Detection rate {rate:.2%} < 95%"


class TestAnonymization:
    def test_pii_not_in_output(self, anonymizer, sample_df):
        """Original CCCD values must not remain after anonymization."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        output_text = df_anon.to_csv(index=False)

        for original_cccd in sample_df["cccd"]:
            assert str(original_cccd) not in output_text

    def test_non_pii_columns_unchanged(self, anonymizer, sample_df):
        """Disease and lab-result columns must remain unchanged."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)

        pd.testing.assert_series_equal(
            sample_df["benh"],
            df_anon["benh"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            sample_df["ket_qua_xet_nghiem"],
            df_anon["ket_qua_xet_nghiem"],
            check_names=False,
        )
