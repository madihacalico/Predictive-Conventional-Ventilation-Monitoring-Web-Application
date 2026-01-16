# database.py
# Handles all database interactions for the Ventilation Prediction System

from sqlalchemy import text

DB_PATH = "ventilation.db"

def initialize_db(conn):
    """
    Create tables if they don't exist
    Expects a SQLAlchemy connection object from st.connection("sql").
    """
    # Table for patient profile (A + B + C): patients
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            height REAL,
            weight REAL,
            comorbid_nkmi INTEGER,
            comorbid_dm INTEGER,
            comorbid_hpt INTEGER,
            comorbid_ihd INTEGER,
            comorbid_ckd INTEGER,
            comorbid_ba INTEGER,
            comorbid_copd INTEGER,
            comorbid_others INTEGER,
            indication_intubation TEXT,
            gcs INTEGER,
            fio2_prior REAL,
            induction_agent TEXT,
            paralytic_agent TEXT,
            ett_size REAL,
            stratified_lung_pathology TEXT,
            sedation TEXT,
            condition TEXT,
            min_tv REAL,
            max_tv REAL,
            min_etco2 REAL,
            max_etco2 REAL,
            min_spo2 REAL,
            max_spo2 REAL,
            max_pplat REAL,
            UNIQUE(patient_id)
        )
    """))

    # Table for ventilation settings (D): vent_settings
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vent_settings (
            patient_id TEXT,
            time INTEGER,
            tv_setting REAL,
            fio2 REAL,
            ventilator_rate REAL,
            ie_ratio REAL,
            peep REAL,
            ps REAL,
            UNIQUE(patient_id, time),
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """))

    # Table for observed/mock data (E): observed_data
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS observed_data (
            patient_id TEXT,
            time INTEGER,
            generated_mv REAL,
            ppeak REAL,
            sbp REAL,
            dbp REAL,
            hr REAL,
            rr REAL,
            ph REAL,
            po2 REAL,
            pco2 REAL,
            hco3 REAL,
            be REAL,
            lactate REAL,
            tv REAL,
            etco2 REAL,
            spo2 REAL,
            pplat REAL,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """))

    # Table for derived features (F): derived_features
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS derived_features (
            patient_id TEXT,
            time INTEGER,
                
            tv_diff,
            tv_pct_change,
            etco2_diff,
            etco2_pct_change,
            spo2_diff,
            spo2_pct_change,
            pplat_diff,
            pplat_pct_change, 

            tv_lag1,
            etco2_lag1,
            spo2_lag1,
            pplat_lag1,
            hr_lag1,
            rr_lag1,
                   
            tv_dist_low,
            tv_dist_high,
            tv_dist_closest,
            etco2_dist_low,
            etco2_dist_high,
            etco2_dist_closest,
            spo2_dist_low,
            spo2_dist_high,
            spo2_dist_closest,
            pplat_dist_low,
            pplat_dist_high,
            pplat_dist_closest,
                       
            tv_in_range,
            etco2_in_range,
            spo2_in_range,
            pplat_in_range,

            ie_ratio_numeric,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """))

    # Table for predictions/output (G)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS predictions (
            patient_id TEXT,
            time INTEGER,
            tv_in_range_next INTEGER,
            etco2_in_range_next INTEGER,
            spo2_in_range_next INTEGER,
            pplat_in_range_next INTEGER,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """))

    # conn.commit()
    # return conn

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

# Get list of patients
def get_all_patients(conn):
    result = conn.execute(text("SELECT patient_id FROM patients"))
    return [row[0] for row in result.fetchall()]

# Get patient data
def get_patient_data(conn, patient_id):
    result = conn.execute(text("SELECT * FROM patients WHERE patient_id=:patient_id"), {"patient_id": patient_id})
    return result.fetchone()

# Get ventilation history for patient
def get_ventilation_history(conn, patient_id):
    sql = "SELECT * FROM vent_settings WHERE patient_id=:patient_id ORDER BY time ASC"
    result = conn.execute(text(sql), {"patient_id": patient_id})
    return result.fetchall()

# Get observed data for patient
def get_observed_history(conn, patient_id):
    sql = "SELECT * FROM observed_data WHERE patient_id=:patient_id ORDER BY time ASC"
    result = conn.execute(text(sql), {"patient_id": patient_id})
    return result.fetchall()

# Get predictions for patient
def get_predictions(conn, patient_id):
    sql = "SELECT * FROM predictions WHERE patient_id=:patient_id ORDER BY time ASC"
    result = conn.execute(text(sql), {"patient_id": patient_id})
    return result.fetchall()

# ----------------- End of database.py ----------------- #
