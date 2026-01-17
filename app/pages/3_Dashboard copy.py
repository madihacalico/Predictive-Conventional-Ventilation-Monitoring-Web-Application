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
from database import get_predictions, get_all_patients
import io
import plotly.io as pio
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


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
# patient_options = patients_df["patient_id"].tolist()
# selected_patient = st.selectbox("Select a patient to view", patient_options)

# ---------- Load patient list ----------
patients_list = get_all_patients(supabase)

if not patients_list:
    st.warning("No patients found. Please add a patient first in Add Patient page.")
    st.stop()

selected_patient = st.selectbox("Select Patient", patients_list)

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
    obs_resp = (
        supabase
        .table("observed_data")
        .select("*")
        .eq("patient_id", selected_patient)
        .order("time_interval")
        .execute()
    )
    obs_df = pd.DataFrame(obs_resp.data)

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
        "etco2": "ETCO2",
        "spo2": "SpO2",
        "pplat": "Plateau Pressure"
    }
    
    st.markdown("### Ventilation Parameters Over Time")

    figures = {}

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

        figures[COL_DISPLAY_NAMES[col]] = fig

    # ------------------------------
    # Display table of historical target status (G)
    # ------------------------------
    st.markdown("### Target Status Prediction History")

    STATUS_DISPLAY_NAMES = {
        "time_interval": "Time (min)",
        "tv_in_range_next": "TV",
        "etco2_in_range_next": "ETCO2",
        "spo2_in_range_next": "SpO2",
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
        (status_df["ETCO2"] == "Out of Range") |
        (status_df["SpO2"] == "Out of Range") |
        (status_df["Plateau Pressure"] == "Out of Range")
    ]["Time (min)"].tolist()

    if out_of_range_times:
        st.warning(f"⚠️ Out-of-range alerts detected at times: {out_of_range_times}")
    else:
        st.success("All parameters predicted to remain in range for this patient.")


def generate_dashboard_pdf(patient_id, figures: dict, status_df: pd.DataFrame):
    """
    Generate a PDF report for a patient with Plotly charts and prediction history table.
    
    Parameters:
    - patient_id: str, selected patient ID
    - figures: dict of Plotly figures, e.g., {'Tidal Volume (TV)': fig, ...}
    - status_df: pandas DataFrame containing prediction history
    """
    # Create temporary PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # --- Title ---
    elements.append(Paragraph(
        f"<b>Ventilation Dashboard Overview</b><br/>Patient ID: {patient_id}",
        styles["Title"]
    ))
    elements.append(Spacer(1, 16))

    # --- Charts ---
    for title, fig in figures.items():
        # Export Plotly figure to PNG in memory
        img_bytes = fig.to_image(format="png", width=800, height=450, engine="kaleido")
        img_buffer = io.BytesIO(img_bytes)

        elements.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 8))
        elements.append(Image(img_buffer, width=500, height=280))
        elements.append(Spacer(1, 16))

    # --- Prediction Table ---
    elements.append(Paragraph("<b>Target Status Prediction History</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    table_data = [status_df.columns.tolist()] + status_df.values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elements.append(table)

    # Build PDF in memory
    doc.build(elements)
    buffer.seek(0)
    return buffer  # return in-memory PDF


st.markdown("---")

if st.button("📄 Export Overview (PDF)"):
    pdf_buffer = generate_dashboard_pdf(
        patient_id=selected_patient,
        figures=figures,
        status_df=status_df
    )

    st.download_button(
        label="⬇️ Download PDF",
        data=pdf_buffer,
        file_name=f"patient_{selected_patient}_dashboard.pdf",
        mime="application/pdf"
    )

