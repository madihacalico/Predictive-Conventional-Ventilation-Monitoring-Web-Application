# utils/feature_engineering.py

import pandas as pd
import numpy as np
import random

from database import get_patient_data, add_derived_features

# ---------- Helper Functions ----------

def parse_ie_ratio(ie_ratio_str):
    """
    Convert IE_Ratio string '1:2' -> float 2.0
    """
    try:
        a, b = ie_ratio_str.split(":")
        return float(b) / float(a)
    except Exception:
        return np.nan

def in_range(value, min_val, max_val):
    """
    Check if value is within min/max range
    """
    if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
        return np.nan
    return int(min_val <= value <= max_val)

# ---------- Generate Mock Observed Data ----------

def generate_mock_observed_data(patient_id, time, supabase):
    """
    Generate mock E data based on patient A-D data stored in DB.
    Returns a dictionary with observed values.
    """
    # Fetch patient info
    patient = get_patient_data(supabase, patient_id)

    # Fetch vent settings for this patient and interval
    response = supabase.table("vent_settings").select("*")\
        .eq("patient_id", patient_id).eq("time", time).execute()
    settings_df = pd.DataFrame(response.data)
    if settings_df.empty:
        raise ValueError(f"No ventilation settings found for patient {patient_id} at time {time}")

    settings = settings_df.iloc[0]

    # Simple mock generation logic
    tv = settings_df['tv_setting'].values[0] + random.randint(-50, 50)
    etco2 = 35 + random.uniform(-5, 5)
    spo2 = 95 + random.uniform(-3, 3)
    pplat = 20 + random.uniform(-3, 3)

    observed_data = {
        # Foreign keys
        "patient_id": patient_id,
        "time": time,

        "generated_mv": tv * settings_df['ventilator_rate'].values[0] / 1000,  # rough estimate
        "ppeak": pplat + random.uniform(0, 2),
        "sbp": 120 + random.randint(-10, 10),
        "dbp": 80 + random.randint(-5, 5),
        "hr": 80 + random.randint(-10, 10),
        "rr": settings_df['ventilator_rate'].values[0],
        "ph": 7.4 + random.uniform(-0.05, 0.05),
        "po2": 90 + random.uniform(-5, 5),
        "pco2": etco2 + random.uniform(-2, 2),
        "hco3": 24 + random.uniform(-2, 2),
        "be": 0 + random.uniform(-2, 2),
        "lactate": 1 + random.uniform(0, 1),
        "tv": tv,
        "etco2": etco2,
        "spo2": spo2,
        "pplat": pplat
    }

    return observed_data

# ---------- Compute Derived Features ----------

def compute_derived_features(patient_id, observed_row, supabase):
    """
    Compute F derived features for patient at current time.
    observed_row: dict containing observed data for this time
    Includes:
        - delta features
        - lag features (previous values)
        - distance to target ranges
        - in-range status
    """
    time = observed_row['time']
    
    # Fetch patient info and target ranges
    patient_response = supabase.table("patients").select("*").eq("patient_id", patient_id).execute()
    if not patient_response.data:
        raise ValueError(f"No patient found with ID {patient_id}")
    patient = patient_response.data[0]

    # Fetch latest vent setting for patient
    vent_response = supabase.table("vent_settings").select("*").eq("patient_id", patient_id).order("time", desc=True).limit(1).execute()
    if not vent_response.data:
        raise ValueError(f"No vent settings found for patient {patient_id}")
    vent_setting = vent_response.data[0]

    # Fetch previous observed row (for lag/delta)
    if time == 0:
        prev_obs = None
    else:
        prev_response = supabase.table("observed_data").select("*").eq("patient_id", patient_id).eq("time", time - 15).execute()
        prev_obs = prev_response.data[0] if prev_response.data else None

    derived = {}

    # ---------- Delta Features ----------
    for var in ['tv', 'etco2', 'spo2', 'pplat']:
        if prev_obs:
            derived[f"{var}_diff"] = observed_row[var] - prev_obs[var]
            derived[f"{var}_pct_change"] = (observed_row[var] - prev_obs[var]) / prev_obs[var] * 100
        else:
            derived[f"{var}_diff"] = np.nan
            derived[f"{var}_pct_change"] = np.nan

    # ---------- Lag Features ----------
    for var in ['tv', 'etco2', 'spo2', 'pplat', 'hr', 'rr']:
        derived[f"{var}_lag1"] = prev_obs[var] if prev_obs else np.nan

    # ---------- Distance to target ranges ----------
    for var, min_col, max_col in [
        ('tv', 'min_tv', 'max_tv'),
        ('etco2', 'min_etco2', 'max_etco2'),
        ('spo2', 'min_spo2', 'max_spo2'),
        ('pplat', None, 'max_pplat')
    ]:
        val = observed_row[var]
        min_val = patient[min_col] if min_col else np.nan
        max_val = patient[max_col]
        if var != 'pplat':
            derived[f"{var}_dist_low"] = val - min_val if min_col else np.nan
        derived[f"{var}_dist_high"] = max_val - val
        derived[f"{var}_dist_closest"] = min(abs(val - min_val) if min_col else np.inf, abs(max_val - val))

    # ---------- In-range status ----------
    derived['tv_in_range'] = in_range(observed_row['tv'], patient['min_tv'], patient['max_tv'])
    derived['etco2_in_range'] = in_range(observed_row['etco2'], patient['min_etco2'], patient['max_etco2'])
    derived['spo2_in_range'] = in_range(observed_row['spo2'], patient['min_spo2'], patient['max_spo2'])
    derived['pplat_in_range'] = in_range(observed_row['pplat'], 0, patient['max_pplat'])

    # ---------- Convert IE_Ratio to numeric ----------
    derived['ie_ratio_numeric'] = parse_ie_ratio(vent_setting.get('ie_ratio', '1:1'))  

    derived['patient_id'] = patient_id
    derived['time'] = time

    # ---------- Insert derived features into Supabase DB ----------
    add_derived_features(supabase, derived)

    return derived