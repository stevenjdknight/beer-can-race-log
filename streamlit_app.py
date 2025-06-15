import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, time, timedelta
import json  # <-- Required for secrets handling

# --- CONFIG ---
st.set_page_config(page_title="🍺 Beer Can Race Log", layout="wide")

# --- TITLE ---
st.title("🍺 Beer Can Scrimmage Race Entry Form")

# --- AUTH ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
gc = gspread.authorize(creds)
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1mAUmYrkc1n37vrTkiZ-J8OsI5SnA7r-nYmdPIR04OZY/edit")
worksheet = sh.worksheet("Race Entries")

# --- FORM ---
with st.form("race_entry_form"):
    st.subheader("Race Details")

    race_date = st.date_input("Race Date (Fridays only)", value=datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper_name = st.text_input("Skipper Name or Nickname")
    boat_type = st.text_input("Boat Type")
    
    # --- START TIME: 18:00 to 20:00, 1-minute steps ---
    start_time_options = [
        (datetime.combine(datetime.today(), time(18, 0)) + timedelta(minutes=i)).time()
        for i in range((20 - 18) * 60 + 1)
    ]
    start_time = st.selectbox("Start Time", start_time_options, index=0)

    finish_time = st.time_input("Finish Time", value=time(19, 0))
    
    elapsed_time = st.text_input("Elapsed Time (HH:MM:SS)")
    corrected_time = st.text_input("Corrected Time (HH:MM:SS)")
    
    island_options = ["Moon", "Duck", "Ramsey", "First Island", "Second Island", "Third Island", "Fourth Island", "Gull Rock", "Snug", "Spooky"]
    marks = [st.selectbox(f"Mark {i+1}", options=[""] + island_options, key=f"mark{i}") for i in range(6)]
    
    comments = st.text_area("Comments or Improvement Ideas")

    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if race_date.weekday() != 4:
            st.error("Race date must be a Friday.")
        elif start_time <= time(17, 59):
            st.error("Start time must be after 17:59.")
        else:
            row = [
                race_date.strftime("%Y-%m-%d"),
                boat_name,
                skipper_name,
                boat_type,
                start_time.strftime("%H:%M"),
                finish_time.strftime("%H:%M"),
                elapsed_time,
                corrected_time,
                *marks,
                comments,
                datetime.now().isoformat()
            ]
            worksheet.append_row(row)
            st.success("Race entry submitted successfully!")
