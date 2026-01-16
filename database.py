# database.py
# Handles all database interactions for the Ventilation Prediction System

from sqlalchemy import text

# ----------------- CRUD Functions ----------------- #

# Add new patient
def add_patient(conn, patient_data: dict):
    """
    patient_data: dictionary containing A+B+C fields
    """
    columns = ", ".join(patient_data.keys())
    values = ", ".join([f":{k}" for k in patient_data.keys()])
    # Columns to update (exclude keys used for uniqueness)
    update_cols = [k for k in patient_data.keys() if k != "patient_id"]
    update_clause = ", ".join([f"{col}=excluded.{col}" for col in update_cols])

    sql = f"""
    INSERT INTO patients ({columns}) 
    VALUES ({values})
    ON CONFLICT(patient_id)
    DO UPDATE SET
    {update_clause}
    """

    conn.execute(text(sql), patient_data)

# Add ventilation settings
def add_vent_settings(conn, vent_data: dict):
    """
    vent_data: dictionary containing patient_id, time, and D fields
    """
    columns = ", ".join(vent_data.keys())
    values = ", ".join([f":{k}" for k in vent_data.keys()])
    # Columns to update (exclude keys used for uniqueness)
    update_cols = [k for k in vent_data.keys() if k not in ("patient_id", "time")]
    update_clause = ", ".join([f"{col}=excluded.{col}" for col in update_cols])

    sql = f"""
    INSERT INTO vent_settings ({columns}) 
    VALUES ({values})
    ON CONFLICT(patient_id, time)
    DO UPDATE SET
    {update_clause}
    """

    conn.execute(text(sql), vent_data)

# Add observed data
def add_observed_data(conn, observed_data: dict):
    """
    observed_data: dictionary containing patient_id, time, and E fields
    """
    columns = ", ".join(observed_data.keys())
    values = ", ".join([f":{k}" for k in observed_data.keys()])
    sql = f"""
    INSERT INTO observed_data ({columns}) 
    VALUES ({values})
    """

    conn.execute(text(sql), observed_data)

# Add derived features
def add_derived_features(conn, derived_features: dict):
    """
    derived_features: dictionary containing patient_id, time, and F fields
    """

    columns = ", ".join(derived_features.keys())
    values = ", ".join([f":{k}" for k in derived_features.keys()])

    sql = f"""
    INSERT INTO derived_features ({columns}) 
    VALUES ({values})
    """

    conn.execute(text(sql), derived_features)

# Add predictions
def add_prediction(conn, patient_id: str, time: int, prediction_data: dict):
    """
    prediction_data: dictionary containing patient_id, time, and G fields
    """
    # Combine patient_id, time, and predictions into a single dictionary
    data_to_insert = {"patient_id": patient_id, "time": time, **prediction_data}

    columns = ", ".join(data_to_insert.keys())
    values = ", ".join([f":{k}" for k in data_to_insert.keys()])

    sql = f"INSERT INTO predictions ({columns}) VALUES ({values})"
    conn.execute(text(sql), data_to_insert)

# # Get list of patients
# def get_all_patients(conn):
#     result = conn.execute(text("SELECT patient_id FROM patients"))
#     return [row[0] for row in result.fetchall()]

# # Get patient data
# def get_patient_data(conn, patient_id):
#     result = conn.execute(text("SELECT * FROM patients WHERE patient_id=:patient_id"), {"patient_id": patient_id})
#     return result.fetchone()

# # Get ventilation history for patient
# def get_ventilation_history(conn, patient_id):
#     sql = "SELECT * FROM vent_settings WHERE patient_id=:patient_id ORDER BY time ASC"
#     result = conn.execute(text(sql), {"patient_id": patient_id})
#     return result.fetchall()

# # Get observed data for patient
# def get_observed_history(conn, patient_id):
#     sql = "SELECT * FROM observed_data WHERE patient_id=:patient_id ORDER BY time ASC"
#     result = conn.execute(text(sql), {"patient_id": patient_id})
#     return result.fetchall()

# # Get predictions for patient
# def get_predictions(conn, patient_id):
#     sql = "SELECT * FROM predictions WHERE patient_id=:patient_id ORDER BY time ASC"
#     result = conn.execute(text(sql), {"patient_id": patient_id})
#     return result.fetchall()

# ----------------- End of database.py ----------------- #
