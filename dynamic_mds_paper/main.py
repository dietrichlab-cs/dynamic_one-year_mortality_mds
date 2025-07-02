import os
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from requests_html import HTMLResponse
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from model_pipeline import LongitudinalFeaturePredictor, BaselineFeaturePredictor

# ---- Configuration ----
# Set the specified environment variable to determine if the app is in development mode
# we assert that dev mode == npm run dev for the vite frontend
is_dev = os.getenv("ENV", "prod") == "dev"
allowed_origins = ["http://localhost:5173"] if is_dev else ["https://dietrichlab.de"]
root_path = "" if is_dev else "/PythonApps/dynamic_mds_paper"

# define app
app = FastAPI()

# ---- Templates & Static ----
# mount static files. This is just needed for production or for running a production-like local instance
# the templates originate from npm run build.
app.mount(f"{root_path}", StaticFiles(directory="dist", html=True), name="static")
# ---- CORS config ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Replace with specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Model DTO ----
class PredictionRequest(BaseModel):
    model: Literal["baseline", "longitudinal"]
    karyotype: Optional[int]
    age: float
    gender: Literal["m", "f"]
    blasts: Optional[float]
    easix: Optional[float] = None
    hb_ed: Optional[float] = None
    leuko_ed: Optional[float] = None
    survival_time: Optional[int] = None
    csv: str

    # we do validate that the csv is not empty if the model is longitudinal
    @model_validator(mode="before")
    def check_csv_if_longitudinal(cls, values):
        if values.get("model") == "longitudinal":
            csv = values.get("csv", "")
            if not csv.strip():
                raise ValueError("CSV content is required for longitudinal model.")
        return values

# ---- Routes ----
# endpoint for prediction
@app.post(f"{root_path}/predict")
def predict(req: PredictionRequest):
    try:
        # Package inputs for the model
        input_data = {
            "model": req.model,
            "karyotype": req.karyotype,
            "age": req.age,
            "gender": req.gender,
            "blasts": req.blasts,
            "easix": req.easix,
            "leuko_ed": req.leuko_ed,
            "hb_ed": req.hb_ed,
            "survival_time": req.survival_time,
            "features": req.csv
        }

        # Call user-defined prediction pipeline
        if input_data["model"] == "longitudinal":
            feature_predictor = LongitudinalFeaturePredictor(input_data)
        else:
            feature_predictor = BaselineFeaturePredictor(input_data)

        # Return structured response
        return {"prediction": str(feature_predictor.get_prediction())}

    except Exception as e:
        raise e
        #raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")