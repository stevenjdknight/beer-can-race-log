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
Welcome to the Beer Can Scrimmage Race Log App! 

To submit a race entry:
1. Fill in your boat and skipper info.
2. Select start and finish times.
3. Choose up to 6 islands rounded.
4. Submit your entry by clicking the button at the bottom.

A **Weekly Leaderboard** is shown for the most recent race week.
An **Annual Leaderboard** will also be displayed at the bottom to track scores over the season.
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
    "Sirius 21": 225,
    "Schock 23": 174,
    "Star": 144,
    "Tanzer 22": 243,
    "Wayfarer": 234
}

# --- FORM ---
with st.form("race_entry_form"):
    st.subheader("Race Details")

    race_date = st.date_input("Race Date (Fridays only)", value=datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper_name = st.text_input("Skipper Name or Nickname")
    boat_type = st.selectbox("Boat Type", sorted(list(phrf_index.keys())))

    # --- START TIME: 18:00 to 20:00 ---
    start_time_options = [
        (datetime.combine(datetime.today(), time(18, 0)) + timedelta(minutes=i)).time()
        for i in range((20 - 18) * 60 + 1)
    ]
    start_time = st.selectbox("Start Time", start_time_options, index=0)

    # --- FINISH TIME: 18:01 to 22:00 ---
    finish_time_options = [
        (datetime.combine(datetime.today(), time(18, 1)) + timedelta(minutes=i)).time()
        for i in range((22 - 18) * 60 - 1)
    ]
    finish_time = st.selectbox("Finish Time", finish_time_options, index=59)

    island_options = ["First Island", "Fourth Island", "Gull Rock", "Moon", "Ramsey", "Second Island", "Snug", "Spooky", "Third Island"]
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

except Exception as e:
    st.warning(f"Could not load leaderboard: {e}")

# --- ANNUAL LEADERBOARD ---
st.subheader("📅 Annual Leaderboard")

try:
    data["Year"] = data["Race Date"].dt.year
    data["Corrected Time"] = pd.to_timedelta(data["Corrected Time"])

    # Get all races per year
    annual = data.copy()
    annual = annual[annual["Corrected Time"].notna()]
    annual = annual.sort_values(["Race Date", "Corrected Time"])

    def assign_annual_points(group):
        total = len(group)
        group = group.reset_index(drop=True)
        group["Points"] = [assign_points(i, total) for i in range(total)]
        return group

    grouped = annual.groupby("Race Date", group_keys=False).apply(assign_annual_points)

    # Sum points by Skipper
    summary = grouped.groupby("Skipper Name or Nickname")["Points"].sum().reset_index()
    summary = summary.sort_values("Points", ascending=False)
    st.dataframe(summary)

except Exception as e:
    st.warning(f"Could not load annual leaderboard: {e}")
