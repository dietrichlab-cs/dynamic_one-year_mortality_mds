import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator, field_validator, model_validator
from typing import Optional, Literal
from fastapi.middleware.cors import CORSMiddleware


from dynamic_mds_paper.model_pipeline import LongitudinalFeaturePredictor, BaselineFeaturePredictor

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

    @model_validator(mode="before")
    def check_csv_if_longitudinal(cls, values):
        if values.get("model") == "longitudinal":
            csv = values.get("csv", "")
            if not csv.strip():
                raise ValueError("CSV content is required for longitudinal model.")
        return values

@app.post("/predict")
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
        print(input_data)
        #predictions = run_predictions(input_data)
        if input_data["model"] == "longitudinal":
            feature_predictor = LongitudinalFeaturePredictor(input_data)
        else:
            feature_predictor = BaselineFeaturePredictor(input_data)

        # Return structured response
        # print(feature_predictor.get_prediction())
        return {"prediction": str(feature_predictor.get_prediction())}

    except Exception as e:
        raise e
        #raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)