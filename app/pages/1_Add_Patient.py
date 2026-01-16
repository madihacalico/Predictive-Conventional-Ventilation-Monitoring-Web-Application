# pages/1_Add_Patient.py
# for streamlit deployment: add root/ to python's import path at runtime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import streamlit as st
from database import add_patient
from supabase import create_client, Client
from Home import init_connection

# Initialize Supabase connection
supabase = init_connection()

st.set_page_config(page_title="Add Patient", layout="wide")
st.title("🧑‍⚕️ Add New Patient")

st.markdown("""
Fill in the patient information below.
This includes **demographics**, **clinical data**, and **target ventilation ranges**.
""")

# --- Demographic Data (A) ---
st.header("Demographic Data")
patient_id = st.text_input("Patient ID (e.g., P001)")
gender = st.selectbox("Gender", ["Male", "Female"])
age = st.number_input("Age", min_value=0, max_value=120, value=30)
height = st.number_input("Height (cm)", min_value=30, max_value=250, value=170)
weight = st.number_input("Weight (kg)", min_value=1, max_value=300, value=70)

st.text("Comorbidities")
comorbid_nkmi = st.checkbox("NKMI")
comorbid_dm = st.checkbox("DM")
comorbid_hpt = st.checkbox("HPT")
comorbid_ihd = st.checkbox("IHD")
comorbid_ckd = st.checkbox("CKD")
comorbid_ba = st.checkbox("BA")
comorbid_copd = st.checkbox("COPD")
comorbid_others = st.checkbox("Other")

# --- Clinical Data (B) ---
st.header("Clinical Data")
# diagnosis = st.text_area("Provisional Diagnosis", placeholder="e.g., HAP with TIRF, anemia")
indication_intubation = st.selectbox(
    "Indication for Intubation",
    ["FAILURE OF OXYGENATION", "AIRWAY OR CEREBRAL PROTECTION", "FAILURE OF VENTILATION", "ANTICIPATE CLINICAL DETERIORATION", ]
)
gcs = st.number_input("GCS", min_value=3, max_value=15, value=15)
# oxygen_requirement_prior = st.text_area("Oxygen Requirement Prior Intubation", 
#                                         placeholder="e.g., NIV FiO2 0.7 PEEP 8 PS 12")
fio2_prior = st.number_input(
    "FiO₂ Prior Intubation (0-1.0)", min_value=0.0, max_value=1.0, value=0.21, step=0.01
)
induction_agent = st.selectbox(
    "Induction Agent", ["Midazolam", "Propofol", "Ketamine", "Other"]
)
paralytic_agent = st.selectbox(
    "Paralytic Agent", ["Rocuronium", "Scolene", "Other"]
)
ett_size = st.number_input("ETT Size (mm)", min_value=2.0, max_value=12.0, value=7.0)
stratified_lung_pathology = st.selectbox(
    "Stratified Lung Pathology", ["RESTRICTIVE LUNG", "NORMAL LUNG (NON PULMONARY)", "OBSTRUCTIVE LUNG"]
)
sedation = st.selectbox("Sedation", ["None", "MIDAZOLAM + FENTANYL", "PROPOFOL + FENTANYL", "Other"])
condition = st.selectbox("Condition", ["ARDS", "NORMAL"])

# --- Patient Target Ranges (C) ---
# kiv: later change so that ranges are automatically calculated from weight
# so can auto display on page after user input weight
st.header("Target Ventilation Ranges")
min_tv = st.number_input("Min TV (mL)", value=400.0)
max_tv = st.number_input("Max TV (mL)", value=600.0)
min_etco2 = st.number_input("Min ETCO₂ (mmHg)", value=35.0)
max_etco2 = st.number_input("Max ETCO₂ (mmHg)", value=45.0)
min_spo2 = st.number_input("Min SpO₂ (%)", value=92.0)
max_spo2 = st.number_input("Max SpO₂ (%)", value=100.0)
max_pplat = st.number_input("Max Pplat (cmH₂O)", value=30.0)

# --- Submit Button ---
if st.button("+ Add Patient", icon="➕"):
    if not patient_id:
        st.error("Patient ID is required!")
    else:
        patient_data = {
            # Demographics (A)
            "patient_id": patient_id,
            "gender": gender,
            "age": age,
            "height": height,
            "weight": weight,
            "comorbid_nkmi": int(comorbid_nkmi),
            "comorbid_dm": int(comorbid_dm),
            "comorbid_hpt": int(comorbid_hpt),
            "comorbid_ihd": int(comorbid_ihd),
            "comorbid_ckd": int(comorbid_ckd),
            "comorbid_ba": int(comorbid_ba),
            "comorbid_copd": int(comorbid_copd),
            "comorbid_others": int(comorbid_others),
            # Clinical (B)
            # "Diagnosis": diagnosis,
            "indication_intubation": indication_intubation,
            "gcs": gcs,
            # "Oxygen_Requirement_Prior_Intubation": oxygen_requirement_prior,
            "fio2_prior": fio2_prior,
            "induction_agent": induction_agent,
            "paralytic_agent": paralytic_agent,
            "ett_size": ett_size,
            "stratified_lung_pathology": stratified_lung_pathology,
            "sedation": sedation,
            "condition": condition,
            # Target ranges (C)
            "min_tv": min_tv,
            "max_tv": max_tv,
            "min_etco2": min_etco2,
            "max_etco2": max_etco2,
            "min_spo2": min_spo2,
            "max_spo2": max_spo2,
            "max_pplat": max_pplat
        }
        try:
            add_patient(supabase, patient_data)
            st.success(f"Patient {patient_id} added successfully!")
        except Exception as e:
            st.error(f"Error adding patient: {e}")
