import streamlit as st
import json
import pandas as pd
from schedule_logic import load_data, get_schedule
import os
from datetime import datetime, date

st.set_page_config(page_title="Smart Ticket Scheduler", layout="centered")
st.title("📋 Smart Ticket Scheduler")
st.markdown("This app helps you plan weekly visits to locations based on submitted support tickets. "
            "It automatically prioritizes busier sites and skips blocked days.")

# --- Location Management Form ---
with st.expander("📍 Manage Locations", expanded=False):
    with st.form("location_form"):
        st.subheader("Add/Remove Locations")
        
        # Load current locations
        try:
            with open("data/locations.json", "r") as f:
                locations_data = json.load(f)
                current_locations = locations_data.get("locations", [])
        except Exception as e:
            st.error(f"Error loading locations: {str(e)}")
            current_locations = []

        # Show current locations with remove buttons
        if current_locations:
            st.write("Current Locations:")
            cols = st.columns(4)
            for i, loc in enumerate(current_locations):
                with cols[i % 4]:
                    if st.button(f"❌ {loc}", key=f"remove_{loc}"):
                        current_locations.remove(loc)
                        try:
                            with open("data/locations.json", "w") as f:
                                json.dump({"locations": current_locations}, f, indent=2)
                            st.success(f"Location '{loc}' removed!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving locations: {str(e)}")

        # Add new location
        new_location = st.text_input("New Location Name")
        add_submitted = st.form_submit_button("Add Location")

        if add_submitted and new_location:
            if new_location not in current_locations:
                current_locations.append(new_location)
                try:
                    with open("data/locations.json", "w") as f:
                        json.dump({"locations": current_locations}, f, indent=2)
                    st.success(f"Location '{new_location}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving locations: {str(e)}")
            else:
                st.warning("This location already exists!")

# --- Ticket Submission Form ---
with st.form("add_ticket_form"):
    st.subheader("➕ Add a New Ticket")
    ticket_name = st.text_input("Ticket Name")
    
    # Load locations for the dropdown
    try:
        with open("data/locations.json", "r") as f:
            locations_data = json.load(f)
            locations = locations_data.get("locations", [])
    except Exception as e:
        st.error(f"Error loading locations: {str(e)}")
        locations = []
    
    location = st.selectbox("Select Location", locations) if locations else st.error("No locations available. Please add some locations first.")
    description = st.text_area("Brief Description")
    ticket_date = st.date_input("Ticket Date", value=date.today())
    submitted = st.form_submit_button("Submit Ticket")

    if submitted and ticket_name and locations:
        try:
            # Load current tickets
            with open("data/tickets.json", "r+") as f:
                tickets = json.load(f)
                tickets.append({
                    "ticket": ticket_name,
                    "location": location,
                    "description": description,
                    "date": ticket_date.strftime("%Y-%m-%d"),
                    "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                f.seek(0)
                json.dump(tickets, f, indent=2)
            st.success(f"✅ Ticket '{ticket_name}' added for {location}.")
        except Exception as e:
            st.error(f"Error saving ticket: {str(e)}")

# --- Load Data ---
try:
    tickets, default_schedule, blocked_days = load_data()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# --- Show Updated Weekly Schedule ---
new_schedule = get_schedule(tickets, default_schedule, blocked_days)
st.subheader("📅 Weekly Schedule")

if new_schedule:
    # Count tickets per location
    location_counts = {}
    for ticket in tickets:
        location = ticket.get("location")
        if location:
            location_counts[location] = location_counts.get(location, 0) + 1

    # Convert schedule dict to DataFrame for calendar-style table
    schedule_df = pd.DataFrame([
        {
            "Day": day,
            "Location": loc,
            "Tickets": f"{location_counts.get(loc, 0)} tickets"
        }
        for day, loc in new_schedule.items()
    ])

    # Set proper weekday order
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    schedule_df["Day"] = pd.Categorical(schedule_df["Day"], categories=weekday_order, ordered=True)
    schedule_df = schedule_df.sort_values("Day")

    # Show table
    st.table(schedule_df)
else:
    st.info("No schedule generated. Please add some tickets to create a schedule.")

# --- Show Submitted Tickets as a Table ---
if tickets:
    st.subheader("📄 Submitted Tickets")
    df = pd.DataFrame(tickets)
    # Sort tickets by date in descending order
    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)
    st.dataframe(df)
else:
    st.info("No tickets submitted yet.")
