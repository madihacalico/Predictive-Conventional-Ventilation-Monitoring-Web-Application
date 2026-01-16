# pages/3_Update_Settings_(Manual).py

import streamlit as st

from utils.feature_engineering import compute_derived_features
from utils.preprocessing import prepare_input_features
from utils.prediction import predict_outcomes
from database import add_vent_settings, add_observed_data, get_all_patients, add_prediction
from Home import init_connection

# ---------- Page UI ----------
st.set_page_config(page_title="Update Settings (Manual Test)", layout="wide")
st.title("🔧 Update Ventilation Settings (Manual Observed Data)")
st.markdown("Purpose of this page: For test users to evaluate model performance accuracy using manually added observed data.")
st.subheader("Add ventilation settings and manually enter observed values for each 15-minute interval")

# ---------- Load patient list ----------
# Initialize database connection
supabase = init_connection()
patients_list = get_all_patients(supabase)

if not patients_list:
    st.warning("No patients found. Please add a patient first in Add Patient page.")
    st.stop()

patient_id = st.selectbox("Select Patient", patients_list)

# ---------- Ventilation Input Form ----------
st.markdown("### Enter Ventilation Settings & Observed Values")

with st.form("vent_settings_form_manual"):
    st.markdown("#### Ventilation settings")
    intervals = list(range(0, 241, 15))
    time_input = st.selectbox("Time (t in minutes)", intervals)

    col1, col2, col3 = st.columns(3)
    with col1:
        tv_setting = st.number_input("TV Setting (mL)", min_value=0, value=400)
    with col2:
        fio2 = st.number_input("FiO2 (0.0 - 1.0)", min_value=0.0, max_value=1.0, step=0.01)
    with col3:
        ventilator_rate = st.number_input("Ventilator Rate (bpm)", min_value=0)

    col4, col5, col6 = st.columns(3)
    with col4:
        ie_ratio = st.text_input("IE Ratio (Format int:int)", value="1:2")
    with col5:
        peep = st.number_input("PEEP (cmH₂O)", min_value=0)
    with col6:
        ps = st.number_input("PS (cmH₂O)", min_value=0)
    
    st.markdown("#### Observed data at time = t")
    #First row
    col7, col8, col9, col10 = st.columns(4)
    with col7:
        tv = st.number_input("TV (mL)", min_value=0)
        generated_mv = st.number_input("Generated MV (L/min)", min_value=0.0, step=0.1)
    with col8:
        etco2 = st.number_input("ETCO₂ (mmHg)", min_value=0.0, step=0.1)
        ppeak = st.number_input("Ppeak (cmH₂O)", min_value=0.0, step=0.1)
    with col9:
        spo2 = st.number_input("SpO₂ (%)", min_value=0.0, max_value=100.0, step=0.1)
        sbp = st.number_input("SBP (mmHg)", min_value=0)
    with col10:
        pplat = st.number_input("Pplat (cmH₂O)", min_value=0.0, step=0.1)
        dbp = st.number_input("DBP (mmHg)", min_value=0)
    
    # Second row
    col11, col12, col13, col14 = st.columns(4)
    with col11:
        hr = st.number_input("Heart Rate (bpm)", min_value=0)
        rr = st.number_input("Respiratory Rate (bpm)", min_value=0)
    with col12:
        ph = st.number_input("pH", min_value=6.8, max_value=7.8, step=0.01)
        po2 = st.number_input("pO₂ (mmHg)", min_value=0.0, step=0.1)
    with col13:
        pco2 = st.number_input("pCO₂ (mmHg)", min_value=0.0, step=0.1)
        hco3 = st.number_input("HCO₃⁻ (mEq/L)", min_value=0.0, step=0.1)
    with col14:
        be = st.number_input("Base Excess (mmol/L)", min_value=-10.0, max_value=10.0, step=0.1)
        lactate = st.number_input("Lactate (mmol/L)", min_value=0.0, step=0.1)


    submitted = st.form_submit_button("➕ Add Data")

# ---------- Process Form Submission ----------
if submitted:
    valid = True
    error_messages = []

    # Validate I:E ratio
    try:
        parts = ie_ratio.split(":")
        if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
            raise ValueError
    except:
        valid = False
        error_messages.append("I:E Ratio must be in format 'int:int', e.g., 1:2, both positive integers.")

    if not valid:
        for msg in error_messages:
            st.error(msg)
    else:
        # Check for duplicate time interval
        existing = supabase.table("vent_settings").select("time_interval").eq("patient_id", patient_id).eq("time_interval", int(time_input)).execute()
        if existing.data:
            st.error(f"Ventilation data for patient {patient_id} at time {time_input} already exists!")
        else:
            # --- Store ventilation settings ---
            vent_data = {
                "patient_id": patient_id,
                "time_interval": int(time_input),
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

            # --- Store manually entered observed data ---
            observed_data = {
              "patient_id": patient_id,
              "time_interval": int(time_input),
              "generated_mv": generated_mv,
              "ppeak": ppeak,
              "sbp": sbp,
              "dbp": dbp,
              "hr": hr,
              "rr": rr,
              "ph": ph,
              "po2": po2,
              "pco2": pco2,
              "hco3": hco3,
              "be": be,
              "lactate": lactate,
              "tv": tv,
              "etco2": etco2,
              "spo2": spo2,
              "pplat": pplat
            }

            add_observed_data(supabase, observed_data)
            st.success("Observed data added to table!")

            # --- Derived features ---
            derived_data = compute_derived_features(patient_id, observed_data, supabase)

            # --- Prepare full feature vector ---
            full_features = prepare_input_features(patient_id, time_input, supabase)

            # --- Predict ---
            predictions = predict_outcomes(full_features)
            add_prediction(supabase, patient_id, time_input, predictions)
            st.success("Predictions generated and saved!")

            # --- Alert Trigger ---
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
