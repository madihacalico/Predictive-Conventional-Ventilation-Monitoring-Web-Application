# database.py
# Handles all database interactions for the Ventilation Prediction System

# from sqlalchemy import text
from supabase import Client

# ----------------- CRUD Functions ----------------- #

# Add new patient
def add_patient(supabase: Client, patient_data: dict):
    """
    Add a new patient or update existing one if patient_id exists.
    Uses Supabase upsert for conflict handling.
    
    supabase: Supabase client
    patient_data: dictionary containing A+B+C fields
    """
    response = supabase.table("patients").upsert(
        patient_data,        # data to insert or update
        on_conflict="patient_id"  # column to check for conflicts
    ).execute()
    
    return response.data

# Add ventilation settings
def add_vent_settings(supabase: Client, vent_data: dict):
    """
    Insert or update ventilation settings for a patient.
    Uses upsert to handle conflicts on patient_id + time.
    
    vent_data: dictionary containing patient_id, time, and D fields
    """
    vent_data = sanitize_for_json(vent_data)
    response = supabase.table("vent_settings").upsert(
        vent_data,        # data to insert or update
        on_conflict="patient_id,time_interval"  # unique constraint on patient_id + time
    ).execute()
    
    return response.data

# Add observed data
def add_observed_data(supabase: Client, observed_data: dict):
    """
    Insert multiple rows of observed data for a patient.
    
    observed_data: dictionary containing patient_id, time, and E fields
    """
    observed_data = sanitize_for_json(observed_data)

    if not observed_data:
        return []
        
    response = supabase.table("observed_data").upsert(
        observed_data,        # data to insert or update
        on_conflict="patient_id,time_interval"  # unique constraint on patient_id + time
    ).execute()
    
    return response.data

# Add derived features
def add_derived_features(supabase: Client, derived_features: dict):
    derived_features = sanitize_for_json(derived_features)
    response = (
        supabase
        .table("derived_features")
        .upsert(
            derived_features,
            on_conflict="patient_id,time_interval"
        )
        .execute()
    )
    return response.data

# Add predictions
def add_prediction(supabase: Client, patient_id: str, time_input: int, predictions: dict):
    """
    Insert or update model predictions for a patient at a given time.
    
    prediction_data: dictionary containing patient_id, time, and G fields
    """
    # Combine patient_id, time_input, and predictions into a single row
    data = {
        "patient_id": patient_id,
        "time_interval": int(time_input),
        **predictions
    }
    response = supabase.table("predictions").upsert(
        data,
        on_conflict="patient_id,time_interval"
    ).execute()
    return response.data

# Get list of patients
def get_all_patients(supabase: Client):
    response = supabase.table("patients").select("patient_id").execute()
    if response.data:
        return [row["patient_id"] for row in response.data]
    else:
        return []

# Get patient data
def get_patient_data(supabase: Client, patient_id):
    """
    Fetch a single patient's full record.
    Returns a dict.
    """
    response = (
        supabase
        .table("patients")
        .select("*")
        .eq("patient_id", patient_id)
        .single()          # ensures one row
        .execute()
    )
    return response.data

# Get vent settings
def get_vent_settings(supabase, patient_id, time):
    """
    Fetch vent settings for a patient at a specific time
    """
    response = (
        supabase
        .table("vent_settings")
        .select("*")
        .eq("patient_id", patient_id)
        .eq("time_interval", time)
        .single()
        .execute()
    )

    return response.data

# Get observed data history for patient
def get_observed_data(
    supabase: Client,
    patient_id: str
) -> pd.DataFrame:
    """
    Fetch observed (E) data for a patient, ordered by time.
    """
    response = (
        supabase
        .table("observed_data")
        .select("*")
        .eq("patient_id", patient_id)
        .order("time_interval")
        .execute()
    )

    return pd.DataFrame(response.data)

# Get predictions history for patient
def get_predictions(
    supabase: Client,
    patient_id: str
) -> pd.DataFrame:
    """
    Fetch prediction (G) data for a patient, ordered by time.
    """
    response = (
        supabase
        .table("predictions")
        .select("*")
        .eq("patient_id", patient_id)
        .order("time_interval")
        .execute()
    )

    return pd.DataFrame(response.data)

# Get derived features
def get_derived_features(supabase, patient_id, time):
    """
    Fetch derived features for a patient at a specific time
    """
    response = (
        supabase
        .table("derived_features")
        .select("*")
        .eq("patient_id", patient_id)
        .eq("time_interval", time)
        .single()
        .execute()
    )

    return response.data

import numpy as np
import pandas as pd
from datetime import datetime, date

def sanitize_for_json(obj):
    """
    Recursively convert objects to JSON-serializable Python types.
    Safe for Supabase / Postgres inserts.
    """
    # Dict
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    # List / tuple
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]

    # NumPy scalars
    if isinstance(obj, np.generic):
        return obj.item()

    # Pandas scalars
    if isinstance(obj, (pd.Timestamp,)):
        return obj.to_pydatetime().isoformat()

    # Datetime / date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # NaN handling
    if obj is None:
        return None

    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass

    return obj

# ----------------- End of database.py ----------------- #
