import sqlite3
from sqlite3 import Error
import os
from database import create_connection

def correct_database():
    conn = create_connection()

    cursor = conn.cursor()
    cursor.executescript("""
        DELETE FROM derived_features WHERE patient_id = 'P002';
        DELETE FROM observed_data WHERE patient_id = 'P002';
        DELETE FROM predictions WHERE patient_id = 'P002';
        DELETE FROM vent_settings WHERE patient_id = 'P002';
    """)

    conn.commit()
    return conn

