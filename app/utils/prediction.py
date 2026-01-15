# utils/prediction.py
import joblib
import json
import pandas as pd
from .preprocessing import preprocess_data  # import your function

MODEL_PATH = "model/ventilation_model_v2.pkl"
FEATURES_PATH = "model/feature_names_v2.json"

# Load model & training column order
model_pipeline = joblib.load(MODEL_PATH)

with open(FEATURES_PATH, "r") as f:
    TRAINING_FEATURES = json.load(f)

def predict_outcomes(feature_dict: dict):
    """
    Accepts raw merged features (A-F) as a dictionary.
    Uses preprocess_data() to prepare the DataFrame for the pipeline.
    Returns a dictionary of predictions for each ventilation variable.
    """

    # Preprocess the input dictionary
    df = preprocess_data(feature_dict)  # returns DataFrame with correct columns

    # Predict using the pipeline
    preds = model_pipeline.predict(df)[0]  # output array [tv, etco2, spo2, pplat]

    # Build output dictionary
    return {
        "tv_in_range_next": int(preds[0]),
        "etco2_in_range_next": int(preds[1]),
        "spo2_in_range_next": int(preds[2]),
        "pplat_in_range_next": int(preds[3]),
    }