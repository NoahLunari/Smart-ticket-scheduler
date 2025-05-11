import streamlit as st
import json
import pandas as pd
from schedule_logic import load_data, get_schedule

st.set_page_config(page_title="Smart Ticket Scheduler", layout="centered")
st.title("📋 Smart Ticket Scheduler")
st.markdown("This app helps you plan weekly visits to locations based on submitted support tickets. "
            "It automatically prioritizes busier sites and skips blocked days.")

# --- Ticket Submission Form ---
with st.form("add_ticket_form"):
    st.subheader("➕ Add a New Ticket")
    ticket_name = st.text_input("Ticket Name")
    location = st.selectbox("Select Location", ["Lan1", "Woodslea", "Main", "Bloor", "Backup"])
    description = st.text_area("Brief Description")
    submitted = st.form_submit_button("Submit Ticket")

    if submitted and ticket_name:
        # Load current tickets
        with open("data/tickets.json", "r+") as f:
            tickets = json.load(f)
            tickets.append({
                "ticket": ticket_name,
                "location": location,
                "description": description
            })
            f.seek(0)
            json.dump(tickets, f, indent=2)
        st.success(f"✅ Ticket '{ticket_name}' added for {location}.")

# --- Load Data ---
tickets, default_schedule, blocked_days = load_data()

# --- Show Updated Weekly Schedule ---
new_schedule = get_schedule(tickets, default_schedule, blocked_days)
st.subheader("📅 Weekly Schedule")
# --- Display schedule ---
st.subheader("📅 Weekly Schedule")

# Convert schedule dict to DataFrame for calendar-style table
schedule_df = pd.DataFrame([
    {"Day": day, "Location": loc}
    for day, loc in schedule.items()
])

# Optional: Set proper weekday order
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
schedule_df["Day"] = pd.Categorical(schedule_df["Day"], categories=weekday_order, ordered=True)
schedule_df = schedule_df.sort_values("Day")

# Show table
st.table(schedule_df)

# --- Show Submitted Tickets as a Table ---
if tickets:
    st.subheader("📄 Submitted Tickets")
    df = pd.DataFrame(tickets)
    st.dataframe(df)
else:
    st.info("No tickets submitted yet.")
