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

def generate_mock_observed_data(patient_id, time, conn):
    """
    Generate mock E data based on patient A-D data stored in DB.
    Returns a dictionary with observed values.
    """
    # Fetch patient info
    # patient_df = pd.read_sql_query(
    #     "SELECT * FROM patients WHERE patient_id = ?", conn, params=(patient_id,)
    # )
    patient = get_patient_data(conn, patient_id)

    settings_df = pd.read_sql_query(
        "SELECT * FROM vent_settings WHERE patient_id = ? AND time = ?",
        conn, params=(patient_id, time)
    )

    # Simple mock generation logic
    # Normally you can replace with statistical models or random ranges based on settings
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

def compute_derived_features(patient_id, observed_df, conn):
    """
    Compute F derived features for patient at current time.
    Includes:
        - delta features
        - lag features (previous values)
        - distance to target ranges
        - in-range status
    """
    time = observed_df['time']
    
    # Fetch patient info and target ranges
    patient = pd.read_sql_query(
        "SELECT * FROM patients WHERE patient_id = ?", conn, params=(patient_id,)
    ).iloc[0]

    vent_setting = pd.read_sql_query(
        "SELECT * FROM vent_settings WHERE patient_id = ?", conn, params=(patient_id,)
    ).iloc[0]
    # patient = get_patient_data(conn, patient_id)

    # Fetch previous observed row (for lag/delta)
    if time == 0:
        prev_obs = None
    else:
        prev_obs_df = pd.read_sql_query(
            "SELECT * FROM observed_data WHERE patient_id = ? AND time = ?",
            conn, params=(patient_id, time - 15)
        )
        prev_obs = prev_obs_df.iloc[0] if not prev_obs_df.empty else None

    derived = {}

    # ---------- Delta Features ----------
    for var in ['tv', 'etco2', 'spo2', 'pplat']:
        if prev_obs is not None:
            derived[f"{var}_diff"] = observed_df[var] - prev_obs[var]
            derived[f"{var}_pct_change"] = (observed_df[var] - prev_obs[var]) / prev_obs[var] * 100
        else:
            derived[f"{var}_diff"] = np.nan
            derived[f"{var}_pct_change"] = np.nan

    # ---------- Lag Features ----------
    for var in ['tv', 'etco2', 'spo2', 'pplat', 'hr', 'rr']:
        if prev_obs is not None:
            derived[f"{var}_lag1"] = prev_obs[var]
        else:
            derived[f"{var}_lag1"] = np.nan

    # ---------- Distance to target ranges ----------
    for var, min_col, max_col in [
        ('tv', 'min_tv', 'max_tv'),
        ('etco2', 'min_etco2', 'max_etco2'),
        ('spo2', 'min_spo2', 'max_spo2'),
        ('pplat', None, 'max_pplat')
    ]:
        val = observed_df[var]
        min_val = patient[min_col] if min_col else np.nan
        max_val = patient[max_col]
        if var != 'pplat':
            derived[f"{var}_dist_low"] = val - min_val if min_col else np.nan
        derived[f"{var}_dist_high"] = max_val - val
        derived[f"{var}_dist_closest"] = min(abs(val - min_val) if min_col else np.inf, abs(max_val - val))

    # ---------- In-range status ----------
    derived['tv_in_range'] = in_range(observed_df['tv'], patient['min_tv'], patient['max_tv'])
    derived['etco2_in_range'] = in_range(observed_df['etco2'], patient['min_etco2'], patient['max_etco2'])
    derived['spo2_in_range'] = in_range(observed_df['spo2'], patient['min_spo2'], patient['max_spo2'])
    derived['pplat_in_range'] = in_range(observed_df['pplat'], 0, patient['max_pplat'])

    # ---------- Convert IE_Ratio to numeric ----------
    # derived['ie_ratio_numeric'] = parse_ie_ratio(patient['ie_ratio'])
    derived['ie_ratio_numeric'] = parse_ie_ratio(vent_setting['ie_ratio'])  
    # if 'ie_ratio' in patient else np.nan

    derived['patient_id'] = patient_id
    derived['time'] = time

    # ---------- Insert derived features into DB ----------
    add_derived_features(conn, derived)

    return derived