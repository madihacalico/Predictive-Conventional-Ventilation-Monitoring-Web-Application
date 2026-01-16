# pages/2_Update_Settings.py
# for streamlit deployment: add root/ to python's import path at runtime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import streamlit as st

from utils.feature_engineering import generate_mock_observed_data, compute_derived_features
from utils.preprocessing import prepare_input_features
from utils.prediction import predict_outcomes
from database import add_vent_settings, add_observed_data, get_all_patients, add_prediction
from Home import init_connection

# ---------- Page UI ----------
st.set_page_config(page_title="Update Settings", layout="wide")
st.title("🔧 Update Ventilation Settings")
st.subheader("Add ventilation settings for each 15-minute interval")


# ---------- Load patient list ----------
# Initialize database connection
supabase = init_connection()
patients_list = get_all_patients(supabase)

if not patients_list:
    st.warning("No patients found. Please add a patient first in Add Patient page.")
    st.stop()

patient_id = st.selectbox("Select Patient", patients_list)

# ---------- Ventilation Input Form ----------
st.markdown("### Enter Ventilation Settings")

with st.form("vent_settings_form"):

    intervals = list(range(0, 241, 15))  # 0, 15, 30, ..., 240
    time_input = st.selectbox("Time (t in minutes)", intervals)

    col1, col2, col3 = st.columns(3)

    with col1:
        tv_setting = st.number_input("tv_Setting (mL)", min_value=0, value=400)

    with col2:
        fio2 = st.number_input("FiO2 (0.0 - 1.0)", min_value=0.0, max_value=1.0, step=0.01)

    with col3:
        ventilator_rate = st.number_input("Ventilator Rate (bpm)", min_value=0)

    col4, col5, col6 = st.columns(3)

    with col4:
        ie_ratio = st.text_input("IE_Ratio (Format int:int)", value="1:2")

    with col5:
        peep = st.number_input("PEEP (cmH₂O)", min_value=0)

    with col6:
        ps = st.number_input("PS (cmH₂O)", min_value=0)

    submitted = st.form_submit_button("➕ Add Data")


# ---------- Process Form Submission ----------
if submitted:
    valid = True
    error_messages = []

    try:
        parts = ie_ratio.split(":")
        if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
            raise ValueError
    except:
        valid = False
        error_messages.append("I:E Ratio must be in format 'int:int', e.g., 1:2, both positive integers.")

    # --- Check if valid before submission ---
    if not valid:
        for msg in error_messages:
            st.error(msg)
    else:
        # --- Check for duplicate time interval ---
        existing = supabase.table("vent_settings").select("time").eq("patient_id", patient_id).eq("time", int(time_input)).execute()
        if existing.data:
            st.error(f"Ventilation data for patient {patient_id} at time {time_input} already exists!")
        else:
            # Store D (vent settings)
            vent_data = {
                "patient_id": patient_id,
                "time": int(time_input),
                "tv_setting": tv_setting,
                "fio2": fio2,
                "ventilator_rate": ventilator_rate,
                "ie_ratio": ie_ratio,
                "peep": peep,
                "ps": ps
            }

            try:
                add_vent_settings(supabase, vent_data)
                st.success(f"Ventilation settings for patient {patient_id} at time {time_input} updated successfully!")
            except Exception as e:
                st.error(f"Error adding ventilation settings: {e}")

            # ---------- E: Generate mock observed data ----------
            observed_data = generate_mock_observed_data(patient_id, vent_data["time"], supabase)
            add_observed_data(supabase, observed_data)
            st.success("Mock data generated and added to table!")

            # ---------- F: Derived features ----------
            derived_data = compute_derived_features(patient_id, observed_data, supabase)

            # ---------- Prepare full feature vector A-F ----------
            full_features = prepare_input_features(patient_id, time_input, supabase)

            # ---------- Predict G ----------
            predictions = predict_outcomes(full_features)
            # Store G
            add_prediction(supabase, patient_id, time_input, predictions)

            st.success("Predictions generated and saved!")

            # ---------- Alert Trigger ----------
            out_of_range = []

            if predictions["tv_in_range_next"] == 0:
                out_of_range.append("Tidal Volume (TV)")
            if predictions["etco2_in_range_next"] == 0:
                out_of_range.append("ETCO₂")
            if predictions["spo2_in_range_next"] == 0:
                out_of_range.append("SpO₂")
            if predictions["pplat_in_range_next"] == 0:
                out_of_range.append("Plateau Pressure")

            if out_of_range:
                message = "⚠️ ALERT: The following parameters are predicted to go OUT OF RANGE:\n\n"
                for item in out_of_range:
                    message += f"• **{item}**\n"
                st.error(message)
            else:
                st.info("All parameters predicted to remain within range.")

            st.info("Dashboard updated with new interval.")
