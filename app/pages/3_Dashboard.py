# pages/3_Dashboard.py
# for streamlit deployment: add root/ to python's import path at runtime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from Home import init_connection
from database import get_observed_data, get_predictions

# ------------------------------
# Supabase connection
# ------------------------------
supabase = init_connection()

# ------------------------------
# Page title
# ------------------------------
st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Conventional Ventilation Dashboard")
st.subheader("Patient Ventilation Overview and Alerts")

# ------------------------------
# Count patients currently undergoing ventilation
# ------------------------------
patients_response = (
    supabase
    .table("patients")
    .select("patient_id")
    .execute()
)
patients_df = pd.DataFrame(patients_response.data).drop_duplicates()
num_patients = len(patients_df)

st.info(f"Number of patients undergoing ventilation: **{num_patients}**")

# ------------------------------
# Patient selection dropdown
# ------------------------------
patient_options = patients_df["patient_id"].tolist()
selected_patient = st.selectbox("Select a patient to view", patient_options)

if selected_patient:

    # ------------------------------
    # Get observed data & predictions
    # ------------------------------
    # vent_resp = (
    #     supabase
    #     .table("vent_settings")
    #     .select("*")
    #     .eq("patient_id", selected_patient)
    #     .order("time_interval")
    #     .execute()
    # )
    # vent_df = pd.DataFrame(vent_resp.data)

    # Observed data
    obs_df = get_observed_data(supabase, selected_patient)

    # Predictions
    pred_df = get_predictions(supabase, selected_patient)

    # Guard clauses
    if obs_df.empty or pred_df.empty:
        st.warning("No data available for this patient yet.")
        st.stop()

    # ------------------------------
    # Merge data for plotting
    # ------------------------------
    # Use observed values for TV, ETCO2, SPO2, Pplat
    plot_df = obs_df[
        ["time_interval", "tv", "etco2", "spo2", "pplat"]
        ]

    # ------------------------------
    # Plot each variable
    # ------------------------------

    COL_DISPLAY_NAMES = {
        "time_interval": "Time (min)",
        "tv": "Tidal Volume (TV)",
        "etco2": "ETCO₂",
        "spo2": "SpO₂",
        "pplat": "Plateau Pressure"
    }
    
    st.markdown("### Ventilation Parameters Over Time")

    for col in ["tv", "etco2", "spo2", "pplat"]:
        fig = px.line(
            plot_df,
            x="time_interval",
            y=col,
            title=f"{COL_DISPLAY_NAMES[col]} over {COL_DISPLAY_NAMES['time_interval']}",
            labels={col: COL_DISPLAY_NAMES[col], "time": COL_DISPLAY_NAMES["time_interval"]},
            markers=True
        )
        st.plotly_chart(fig, width="stretch")

    # ------------------------------
    # Display table of historical target status (G)
    # ------------------------------
    st.markdown("### Target Status Prediction History")

    STATUS_DISPLAY_NAMES = {
        "time_interval": "Time (min)",
        "tv_in_range_next": "TV",
        "etco2_in_range_next": "ETCO₂",
        "spo2_in_range_next": "SpO₂",
        "pplat_in_range_next": "Plateau Pressure"
    }
    status_cols = list(STATUS_DISPLAY_NAMES.keys())
    status_df = pred_df[status_cols].copy()

    # Map 0/1 to human-readable except for time
    status_df[list(STATUS_DISPLAY_NAMES.keys())[1:]] = status_df[list(STATUS_DISPLAY_NAMES.keys())[1:]].replace({0: "Out of Range", 1: "In Range"})
    # Rename columns for display
    status_df.rename(columns=STATUS_DISPLAY_NAMES, inplace=True)

    st.dataframe(status_df, width="stretch")

    # ------------------------------
    # Optional: highlight out-of-range intervals
    # ------------------------------
    out_of_range_times = status_df[
        (status_df["TV"] == "Out of Range") |
        (status_df["ETCO₂"] == "Out of Range") |
        (status_df["SpO₂"] == "Out of Range") |
        (status_df["Plateau Pressure"] == "Out of Range")
    ]["Time (min)"].tolist()

    if out_of_range_times:
        st.warning(f"⚠️ Out-of-range alerts detected at times: {out_of_range_times}")
    else:
        st.success("All parameters predicted to remain in range for this patient.")

