import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, time, timedelta
import json

# --- CONFIG ---
st.set_page_config(page_title="🍺 Beer Can Race Log", layout="wide")

# --- TITLE ---
st.title("🍺 Beer Can Scrimmage Race Entry Form")

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
### 🏁 Scoring System
Each race is scored based on the number of participating boats:
- **1 boat** → 1 point  
- **2 boats** → 2 pts for 1st, 1 for 2nd  
- **3 boats** → 3 pts / 2 pts / 1 pt  
- **4+ boats** → 4 pts for 1st, 3 pts for 2nd, 2 pts for 3rd, 1 pt for all others  

Scoring is ranked by **Corrected Time**.
""")

# --- AUTH ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
gc = gspread.authorize(creds)
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1mAUmYrkc1n37vrTkiZ-J8OsI5SnA7r-nYmdPIR04OZY/edit")
worksheet = sh.worksheet("Race Entries")

# --- PHRF Ratings (simplified multiplier: 1 + rating/10000) ---
phrf_index = {
    "Albacore": 239,
    "CL16": 255,
    "Crown 26": 218,
    "Hunter 22": 216,
    "Laser": 126,
    "Schock 23": 174,
    "Star": 144,
    "Sirius 21": 225,
    "Tanzer 22": 243,
    "Wayfarer": 234,
    "Not Listed - Add in comments": 000,
}

# --- FORM ---
with st.form("race_entry_form"):
    st.subheader("Race Details")

    race_date = st.date_input("Race Date (Fridays only)", value=datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper_name = st.text_input("Skipper Name or Nickname")
    boat_type = st.selectbox("Boat Type", list(phrf_index.keys()))

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
            phrf = phrf_index.get(boat_type, 0)
            multiplier = 1 + (phrf / 10000)
            corrected = elapsed * multiplier

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

# --- WEEKLY LEADERBOARD ---
st.subheader("📊 Weekly Leaderboard")

try:
    expected_headers = [
        "Race Date", "Boat Name", "Skipper Name or Nickname", "Boat Type",
        "Start Time", "Finish Time", "Elapsed Time", "Corrected Time",
        "Mark 1", "Mark 2", "Mark 3", "Mark 4", "Mark 5", "Mark 6",
        "Comments or Improvement Ideas", "Submission Timestamp"
    ]
    data = pd.DataFrame(worksheet.get_all_records(expected_headers=expected_headers))
    data["Race Date"] = pd.to_datetime(data["Race Date"])
    latest_friday = data["Race Date"].max()
    week_data = data[data["Race Date"] == latest_friday].copy()

    week_data = week_data[week_data["Corrected Time"].str.strip() != ""]
    week_data["Corrected Time"] = pd.to_timedelta(week_data["Corrected Time"])
    week_data["Elapsed Time"] = pd.to_timedelta(week_data["Elapsed Time"])
    week_data = week_data.sort_values("Corrected Time")

    num_boats = len(week_data)

    def assign_points(rank, total):
        if total == 1:
            return 1
        elif total == 2:
            return 2 - rank if rank < 2 else 0
        elif total == 3:
            return max(0, 3 - rank)
        elif total >= 4:
            if rank == 0:
                return 4
            elif rank == 1:
                return 3
            elif rank == 2:
                return 2
            else:
                return 1
        return 0

    week_data["Points"] = [assign_points(i, num_boats) for i in range(num_boats)]

    st.dataframe(week_data[[
        "Skipper Name or Nickname",
        "Boat Name",
        "Elapsed Time",
        "Corrected Time",
        "Points"
    ]])

    # --- ANNUAL LEADERBOARD ---
    st.subheader("\U0001f3c6 Annual Leaderboard")
    data = data[data["Corrected Time"].str.strip() != ""]
    data["Corrected Time"] = pd.to_timedelta(data["Corrected Time"])
    data["Elapsed Time"] = pd.to_timedelta(data["Elapsed Time"])
    data = data.sort_values("Race Date")
    data["Race Year"] = data["Race Date"].dt.year

    def compute_annual_points(df):
        result_rows = []
        for date, group in df.groupby("Race Date"):
            group = group.sort_values("Corrected Time").reset_index(drop=True)
            total = len(group)
            for i, row in group.iterrows():
                points = assign_points(i, total)
                result_rows.append({
                    "Skipper Name or Nickname": row["Skipper Name or Nickname"],
                    "Race Year": row["Race Year"],
                    "Points": points
                })
        result_df = pd.DataFrame(result_rows)
        return result_df.groupby(["Race Year", "Skipper Name or Nickname"]).sum().reset_index()

    annual = compute_annual_points(data)
    latest_year = annual["Race Year"].max()
    leaderboard = annual[annual["Race Year"] == latest_year].sort_values("Points", ascending=False)

    st.dataframe(leaderboard)

except Exception as e:
    st.warning(f"Could not load leaderboard: {e}")
