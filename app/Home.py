
# Home.py: home page/landing page
# to run file: streamlit run app/Home.py

# for streamlit deployment: add root/ to python's import path at runtime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import streamlit as st
import joblib
import os
from database import initialize_db
from database_correction import correct_database

# Initial Setup
st.set_page_config(
    page_title="Ventilation Decision Support System",
    page_icon="🫁",
    layout="wide"
)

# Load model + feature names

@st.cache_resource
def load_model():
    # model = joblib.load("model/ventilation_model.pkl")
    model = joblib.load("model/ventilation_model_v2.pkl")
    return model

@st.cache_resource
def load_feature_names():
    import json
    # with open("model/feature_names.json", "r") as f:
    #     return json.load(f)
    with open("model/feature_names_v2.json", "r") as f:
        return json.load(f)

model = load_model()
feature_names = load_feature_names()

# Database Connection

DB_PATH = "ventilation.db"

initialize_db()
# comment line below if no database correction needed
# correct_database()

# Home Page Content

st.title("🫁 Ventilation Prediction System")
st.subheader("Decision Support Tool for Conventional Mechanical Ventilation (Prototype)")

st.markdown("""
Welcome to the **Ventilation Prediction Dashboard**.

Use the sidebar to navigate:
- **Page 1 – Add Patient**
- **Page 2 – Update Ventilation Settings**
- **Page 3 – Patient Dashboard**

This system allows clinicians to:
- Enter patient demographic and clinical data  
- Add ventilator settings every 15 minutes  
- Automatically generate mock observed data  
- Compute derived features  
- Predict whether TV, ETCO₂, SpO₂, and Pplat will remain **in-range** in the next interval  
- Trigger alerts when risk of deterioration is detected  
""")

# Show basic model info

with st.expander("Model Information"):
    st.write("Model type:", type(model).__name__)
    st.write("Number of features expected:", len(feature_names))
    st.write("Feature list:")
    st.code(", ".join(feature_names))

# Database check

with st.expander("Database Status"):
    if os.path.exists(DB_PATH):
        st.success(f"Database located at: {DB_PATH}")
    else:
        st.error("Database not created yet.")

st.markdown("---")
st.info("Go to the sidebar to begin.")
