import pandas as pd
import pytest

from src.pii.anonymizer import MedVietAnonymizer
from src.quality.validation import (
    RAW_DATA_PATH,
    build_patient_expectation_suite,
    validate_anonymized_data,
)


@pytest.fixture
def anonymized_csv(tmp_path):
    df = pd.read_csv(RAW_DATA_PATH, dtype={"cccd": str, "so_dien_thoai": str})
    df_anon = MedVietAnonymizer().anonymize_dataframe(df)
    output_path = tmp_path / "patients_anonymized.csv"
    df_anon.to_csv(output_path, index=False)
    return output_path


def test_build_patient_expectation_suite():
    suite = build_patient_expectation_suite()
    assert suite.name == "patient_data_suite"
    assert len(suite.expectations) >= 6


def test_validate_anonymized_data_success(anonymized_csv):
    result = validate_anonymized_data(str(anonymized_csv))
    assert result["success"] is True
    assert result["failed_checks"] == []


def test_validate_anonymized_data_missing_file():
    result = validate_anonymized_data("data/processed/does_not_exist.csv")
    assert result["success"] is False
    assert any("File not found" in check for check in result["failed_checks"])
