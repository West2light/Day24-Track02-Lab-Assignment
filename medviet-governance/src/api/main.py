# src/api/main.py
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "patients_raw.csv"


def load_raw_patients() -> pd.DataFrame:
    if not RAW_DATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Raw patient dataset not found. Run scripts/generate_data.py "
                "before starting the API."
            ),
        )

    return pd.read_csv(RAW_DATA_PATH)


@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    """
    Return the first 10 raw patient records. Only admins may access this.
    """
    df = load_raw_patients()
    records = df.head(10).to_dict(orient="records")
    return JSONResponse(content={"count": len(records), "data": records})


@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    """
    Return anonymized training data for admin and ml_engineer.
    """
    df = load_raw_patients()
    df_anon = anonymizer.anonymize_dataframe(df)
    records = df_anon.head(10).to_dict(orient="records")
    return JSONResponse(content={"count": len(records), "data": records})


@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    """
    Return non-PII aggregated patient counts by disease type.
    """
    df = load_raw_patients()
    metrics = (
        df["benh"]
        .value_counts(dropna=False)
        .rename_axis("benh")
        .reset_index(name="patient_count")
        .to_dict(orient="records")
    )
    return JSONResponse(content={"count": len(metrics), "data": metrics})


@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Mock delete endpoint. Only admins may delete patient data.
    """
    return JSONResponse(
        content={
            "status": "deleted",
            "patient_id": patient_id,
            "deleted_by": current_user["username"],
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
