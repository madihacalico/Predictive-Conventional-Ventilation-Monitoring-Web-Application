# utils/preprocessing.py

import pandas as pd
import json
import os

from database import (
    get_patient_data,
    get_vent_settings,
    get_observed_data,
    get_derived_features
)

# Load the feature names used during training
FEATURES_PATH = "model/feature_names_v2.json"

if not os.path.exists(FEATURES_PATH):
    raise FileNotFoundError(f"{FEATURES_PATH} not found. Ensure it is saved during training.")

with open(FEATURES_PATH, "r") as f:
    TRAIN_FEATURES = json.load(f)

def prepare_input_features(patient_id, time, supabase):
    """
    Build a single feature vector (A–F) for prediction.

    Returns:
        dict: raw feature values keyed by feature name
    """

    # ---------- Load patient data ----------
    patient = get_patient_data(supabase, patient_id)
    if not patient:
        raise ValueError(f"No patient found for {patient_id}")

    # ---------- Load vent settings ----------
    vent = get_vent_settings(supabase, patient_id, time)
    if not vent:
        raise ValueError(f"No vent settings for {patient_id} at time {time}")

    # ---------- Load observed data ----------
    obs = get_observed_data(supabase, patient_id, time)
    if not obs:
        raise ValueError(f"No observed data for {patient_id} at time {time}")

    # ---------- Load derived features ----------
    derived = get_derived_features(supabase, patient_id, time)
    if not derived:
        raise ValueError(f"No derived features for {patient_id} at time {time}")

    # ---------- Merge all features ----------
    features = {}
    features.update(patient)
    features.update(vent)
    features.update(obs)
    features.update(derived)

    # ---------- Remove non-feature columns ----------
    # Keep only columns that are in TRAIN_FEATURES
    features = {k: features.get(k) for k in TRAIN_FEATURES}

    return features

def preprocess_data(input_dict):
    """
    Prepare incoming raw feature values for the prediction pipeline.

    - Converts dictionary to DataFrame
    - Ensures correct column order based on training features
    - Fills any missing required fields with None (pipeline will handle them)
    """

    # Convert input to DataFrame
    df = pd.DataFrame([input_dict])

    # Ensure all expected columns exist (missing columns will be set to None)
    for col in TRAIN_FEATURES:
        if col not in df.columns:
            df[col] = None

    # Reorder columns to match training order
    df = df[TRAIN_FEATURES]

    return df