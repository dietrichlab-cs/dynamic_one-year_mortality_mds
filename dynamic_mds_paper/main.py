import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, Literal
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

from dynamic_mds_paper.model_pipeline import LongitudinalFeaturePredictor

# Placeholder import
#from my_model_lib import run_predictions  # your prediction pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DATE = datetime(2000, 1, 1)

class PredictionRequest(BaseModel):
    model: Literal["baseline", "longitudinal"]
    karyotype: Optional[int]
    age: float
    gender: Literal["m", "f"]
    blasts: Optional[float]
    easix: Optional[float] = None
    csv: str

    @field_validator("csv")
    def check_csv_not_empty(cls, v):
        if not v.strip():
            raise ValueError("CSV content is empty")
        return v

@app.post("/predict")
def predict(req: PredictionRequest):
    try:
        if len(req.csv.strip().splitlines()) < 2:
            raise HTTPException(status_code=400, detail="CSV must contain header and at least one row.")
        df = pd.read_csv(StringIO(req.csv), index_col=0)

        # Ensure index is numeric days
        try:
            df.index = pd.to_numeric(df.index)
        except Exception:
            raise HTTPException(status_code=400, detail="CSV index must be numeric day offsets.")
        # 🆕 Drop duplicate day offsets, keep only the first occurrence
        df = df[~df.index.duplicated(keep="first")]
        # Convert index to datetime
        df.index = [BASE_DATE + timedelta(days=int(d)) for d in df.index]
        df.index.name = "date"

        # Package inputs for the model
        input_data = {
            "model": req.model,
            "karyotype": req.karyotype,
            "age": req.age,
            "gender": req.gender,
            "blasts": req.blasts,
            "easix": req.easix,
            "features": df
        }

        # Call user-defined prediction pipeline
        print(input_data)
        #predictions = run_predictions(input_data)
        feature_predictor = LongitudinalFeaturePredictor(input_data)
        feature_predictor.get_prediction()

        # Return structured response
        return {"prediction": "0.5"}

    except Exception as e:
        raise e
        #raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)