import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, time, timedelta
import json

# --- CONFIG ---
st.set_page_config(page_title=" Beer Can Race Log (BCS)", layout="wide")

# --- TITLE ---
st.title(" Beer Can Scrimmage Race Entry Form")

# --- INSTRUCTIONS ---
st.markdown("""
### ℹ️ Instructions
To log your race:
- Ensure the race was held on a **Friday**
- Provide start and finish times using the dropdowns
- Choose up to 6 islands (marks) rounded during the race
- Your race result will appear on the weekly leaderboard

**Note:** Both weekly and annual leaderboards are displayed. If no new entry is submitted this week, the last race's results will continue to show.
""")

# --- SCORING SYSTEM INFO ---
st.markdown("""
### 🏍️ Scoring System
Each race is scored based on the number of participating boats:
- **1 boat** → 1 point  
- **2 boats** → 2 pts for 1st, 1 for 2nd  
- **3 boats** → 3 pts / 2 pts / 1 pt  
- **4+ boats** → 4 pts for 1st, 3 pts for 2nd, 2 pts for 3rd, 1 pt for all others  

Scoring is ranked by **Corrected Time using Portsmouth-based multiplier**.
""")

# --- AUTH ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
gc = gspread.authorize(creds)
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1mAUmYrkc1n37vrTkiZ-J8OsI5SnA7r-nYmdPIR04OZY/edit")
worksheet = sh.worksheet("Race Entries")

# --- Portsmouth Ratings (simplified multiplier: 100 / rating) ---
portsmouth_index = {
    "29er": 78.0,
    "Abbott 22": 95.0,
    "Albacore": 92.8,
    "Ancom 23": 95.0,
    "Capricorn": 91.0,
    "Catalina 22": 96.3,
    "CL16": 97.5,
    "Crown 26": 91.5,
    "Hunter 22": 90.0,
    "Laser": 91.1,
    "Laser II": 88.0,
    "Mutineer 15": 91.4,
    "Optimist": 123.6,
    "Paceship 23": 96.0,
    "Sandpiper": 105.0,
    "Schock 23": 89.0,
    "Serious 21": 92.5,
    "Siren": 101.2,
    "Sirius 21": 92.5,
    "Sirius 22": 93.0,
    "Siris 2": 93.0,
    "Soling": 83.0,
    "Star": 87.0,
    "Tanzer 22": 94.0,
    "Tanzer 26": 90.5,
    "Tanzer 7.5": 91.0,
    "Venture macgregor": 96.0,
    "Wayfarer": 95.5,
    "Y-Flyer": 90.0,
    "Not Listed - Add in comments": 100.0
}

# --- FORM ---
with st.form("race_entry_form"):
    st.subheader("Race Details")

    race_date = st.date_input("Race Date (Fridays only)", value=datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper_name = st.text_input("Skipper Name or Nickname")
    boat_type = st.selectbox("Boat Type", sorted(list(portsmouth_index.keys())))

    start_time_options = [
        (datetime.combine(datetime.today(), time(18, 0)) + timedelta(minutes=i)).time()
        for i in range((20 - 18) * 60 + 1)
    ]
    start_time = st.selectbox("Start Time", start_time_options, index=0)

    finish_time_options = [
        (datetime.combine(datetime.today(), time(18, 1)) + timedelta(minutes=i)).time()
        for i in range((22 - 18) * 60 - 1)
    ]
    finish_time = st.selectbox("Finish Time", finish_time_options, index=59)

    island_options = ["Potter Island", "Swiss Island", "McCrea Island", "Norway Island", "Berry Island", "Swansea Island", "Galliard, Bass & Pike Island", "Gull Rock", "Snug", "Spooky"]
    marks = [st.selectbox(f"Mark {i+1}", options=[""] + island_options, key=f"mark{i}") for i in range(6)]

    comments = st.text_area("Comments or Improvement Ideas")

    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if race_date.weekday() != 4:
            st.error("Race date must be a Friday.")
        elif start_time <= time(17, 59):
            st.error("Start time must be after 17:59.")
        else:
            today = datetime.today()
            start_dt = datetime.combine(today, start_time)
            finish_dt = datetime.combine(today, finish_time)
            elapsed = finish_dt - start_dt

            portsmouth_rating = portsmouth_index.get(boat_type, 100.0)
            multiplier = 100.0 / portsmouth_rating if portsmouth_rating else 1.0
            corrected = timedelta(seconds=elapsed.total_seconds() * multiplier)

            row = [
                race_date.strftime("%Y-%m-%d"),
                boat_name,
                skipper_name,
                boat_type,
                start_time.strftime("%H:%M"),
                finish_time.strftime("%H:%M"),
                str(elapsed),
                str(corrected),
                *marks,
                comments,
                datetime.now().isoformat()
            ]
            worksheet.append_row(row)
            st.success("Race entry submitted successfully!")
