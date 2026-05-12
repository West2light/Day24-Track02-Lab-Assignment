# src/quality/validation.py
from pathlib import Path
import re

import pandas as pd
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.expectations.expectation_configuration import (
    ExpectationConfiguration,
)


VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
RAW_CCCD_REGEX = re.compile(r"^\d{12}$")
IMPORTANT_COLUMNS = ["patient_id", "cccd", "email", "benh", "ket_qua_xet_nghiem"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "patients_raw.csv"


def build_patient_expectation_suite() -> ExpectationSuite:
    """
    Build a Great Expectations suite for patient data validation.
    """
    suite = ExpectationSuite(name="patient_data_suite")
    suite.expectations = [
        ExpectationConfiguration(
            type="expect_column_values_to_not_be_null",
            kwargs={"column": "patient_id"},
        ),
        ExpectationConfiguration(
            type="expect_column_value_lengths_to_equal",
            kwargs={"column": "cccd", "value": 12},
        ),
        ExpectationConfiguration(
            type="expect_column_values_to_be_between",
            kwargs={
                "column": "ket_qua_xet_nghiem",
                "min_value": 0,
                "max_value": 50,
            },
        ),
        ExpectationConfiguration(
            type="expect_column_values_to_be_in_set",
            kwargs={"column": "benh", "value_set": VALID_CONDITIONS},
        ),
        ExpectationConfiguration(
            type="expect_column_values_to_match_regex",
            kwargs={"column": "email", "regex": EMAIL_REGEX},
        ),
        ExpectationConfiguration(
            type="expect_column_values_to_be_unique",
            kwargs={"column": "patient_id"},
        ),
    ]
    return suite


def validate_anonymized_data(filepath: str) -> dict:
    """
    Validate anonymized patient data and return a simple summary payload.
    """
    target_path = Path(filepath)
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "filepath": str(target_path),
            "total_rows": 0,
            "columns": [],
        },
    }

    if not target_path.exists():
        results["success"] = False
        results["failed_checks"].append(f"File not found: {target_path}")
        return results

    df = pd.read_csv(target_path, dtype={"cccd": str, "so_dien_thoai": str})
    results["stats"]["total_rows"] = len(df)
    results["stats"]["columns"] = list(df.columns)

    missing_columns = [column for column in IMPORTANT_COLUMNS if column not in df.columns]
    if missing_columns:
        results["success"] = False
        results["failed_checks"].append(
            f"Missing required columns: {', '.join(missing_columns)}"
        )
        return results

    if df[IMPORTANT_COLUMNS].isnull().any().any():
        results["success"] = False
        results["failed_checks"].append(
            "Important columns contain null values."
        )

    if RAW_DATA_PATH.exists():
        raw_df = pd.read_csv(RAW_DATA_PATH, dtype={"cccd": str, "so_dien_thoai": str})
        raw_cccd_set = set(raw_df["cccd"].astype(str))
        anonymized_cccd_set = set(df["cccd"].astype(str))

        if raw_cccd_set.intersection(anonymized_cccd_set):
            results["success"] = False
            results["failed_checks"].append(
                "Column 'cccd' still contains original raw identifiers."
            )

        if len(df) != len(raw_df):
            results["success"] = False
            results["failed_checks"].append(
                f"Row count mismatch: anonymized={len(df)}, raw={len(raw_df)}"
            )

    if not df["email"].astype(str).str.fullmatch(EMAIL_REGEX).all():
        results["success"] = False
        results["failed_checks"].append("Column 'email' contains invalid values.")

    if not df["benh"].isin(VALID_CONDITIONS).all():
        results["success"] = False
        results["failed_checks"].append("Column 'benh' contains invalid conditions.")

    if not df["patient_id"].is_unique:
        results["success"] = False
        results["failed_checks"].append("Column 'patient_id' contains duplicates.")

    ket_qua = pd.to_numeric(df["ket_qua_xet_nghiem"], errors="coerce")
    if ket_qua.isnull().any() or not ket_qua.between(0, 50).all():
        results["success"] = False
        results["failed_checks"].append(
            "Column 'ket_qua_xet_nghiem' contains values outside [0, 50]."
        )

    return results
