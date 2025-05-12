import streamlit as st
import json
import pandas as pd
from schedule_logic import load_data, get_schedule
import os
from datetime import datetime, date
import uuid
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.grid_options_builder import GridOptionsBuilder

def generate_ticket_id():
    """Generate a unique ticket ID"""
    return str(uuid.uuid4())

def is_duplicate_ticket(ticket_name, location, date):
    """Check if a ticket with the same name, location, and date already exists"""
    try:
        with open("data/tickets.json", "r") as f:
            tickets = json.load(f)
            return any(
                t["ticket"] == ticket_name and 
                t["location"] == location and 
                t["date"] == date 
                for t in tickets
            )
    except Exception:
        return False

def archive_ticket(ticket):
    """Archive a ticket by moving it to the archived_tickets.json file"""
    try:
        # Convert pandas Series to dict if needed
        if isinstance(ticket, pd.Series):
            ticket = ticket.to_dict()
            
        # Load current archived tickets
        with open("data/archived_tickets.json", "r") as f:
            archived_data = json.load(f)
            archived_tickets = archived_data.get("archived_tickets", [])
        
        # Add archive timestamp
        ticket["archived_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add to archived tickets
        archived_tickets.append(ticket)
        
        # Save updated archived tickets
        with open("data/archived_tickets.json", "w") as f:
            json.dump({"archived_tickets": archived_tickets}, f, indent=2)
            
        return True
    except Exception as e:
        st.error(f"Error archiving ticket: {str(e)}")
        return False

def lock_ticket_to_day(ticket_id, day):
    """Lock a ticket to a specific day"""
    try:
        with open("data/locked_tickets.json", "r+") as f:
            locked_data = json.load(f)
            locked_data["locked_tickets"][day] = ticket_id
            f.seek(0)
            f.truncate()
            json.dump(locked_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error locking ticket: {str(e)}")
        return False

def unlock_day(day):
    """Remove lock from a day"""
    try:
        with open("data/locked_tickets.json", "r+") as f:
            locked_data = json.load(f)
            locked_data["locked_tickets"][day] = null
            f.seek(0)
            f.truncate()
            json.dump(locked_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error unlocking day: {str(e)}")
        return False

st.set_page_config(page_title="Smart Ticket Scheduler", layout="centered")
st.title("📋 Smart Ticket Scheduler")
st.markdown("This app helps you plan weekly visits to locations based on submitted support tickets. "
            "It automatically prioritizes busier sites and skips blocked days.")

# --- Location Management Form ---
with st.expander("📍 Manage Locations", expanded=False):
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

    # Add new location form
    with st.form("location_form"):
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
        # Check for duplicate ticket
        if is_duplicate_ticket(ticket_name, location, ticket_date.strftime("%Y-%m-%d")):
            st.error("A ticket with this name already exists for this location and date!")
        else:
            try:
                # Load current tickets
                with open("data/tickets.json", "r+") as f:
                    tickets = json.load(f)
                    tickets.append({
                        "ticket_id": generate_ticket_id(),
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
    tickets, default_schedule, locked_tickets = load_data()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# --- Show Updated Weekly Schedule ---
new_schedule = get_schedule(tickets, default_schedule, locked_tickets)
st.subheader("📅 Weekly Schedule")

if new_schedule:
    # Count tickets per location
    location_counts = {}
    for ticket in tickets:
        location = ticket.get("location")
        if location:
            location_counts[location] = location_counts.get(location, 0) + 1

    # Create a more detailed DataFrame for the grid
    schedule_data = []
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    for day in weekday_order:
        location = new_schedule.get(day, "Not Scheduled")
        ticket_count = location_counts.get(location, 0)
        day_tickets = [t for t in tickets if t["location"] == location]
        
        # Check if day has a locked ticket
        locked_ticket_id = locked_tickets["locked_tickets"].get(day)
        locked_ticket = next((t for t in tickets if t["ticket_id"] == locked_ticket_id), None) if locked_ticket_id else None
        
        # Get the latest tickets for this location, highlighting locked ticket if present
        latest_tickets = []
        for t in day_tickets[:3]:
            if locked_ticket and t["ticket_id"] == locked_ticket["ticket_id"]:
                latest_tickets.append(f"🔒 {t['ticket']}")
            else:
                latest_tickets.append(t["ticket"])
        
        schedule_data.append({
            "Day": day,
            "Location": location,
            "Ticket Count": ticket_count,
            "Status": "🔒 Locked" if locked_ticket else "✅ Available",
            "Latest Tickets": ", ".join(latest_tickets)
        })
    
    schedule_df = pd.DataFrame(schedule_data)
    
    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(schedule_df)
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sorteable=True,
        editable=False
    )
    
    # Customize column properties
    gb.configure_column("Day", pinned="left", width=120)
    gb.configure_column("Location", width=150)
    gb.configure_column("Ticket Count", width=120)
    gb.configure_column("Status", width=120)
    gb.configure_column("Latest Tickets", width=300)
    
    # Set theme and other grid options
    grid_options = gb.build()
    grid_options['domLayout'] = 'autoHeight'
    
    # Render the grid
    grid_response = AgGrid(
        schedule_df,
        gridOptions=grid_options,
        theme="streamlit",
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=300
    )
    
    # Add ticket details section below the grid
    st.subheader("📝 Location Details and Ticket Management")
    selected_day = st.selectbox("Select Day to View Details", weekday_order)
    
    if selected_day:
        location = new_schedule.get(selected_day)
        if location:
            # Check if day is locked
            locked_ticket_id = locked_tickets["locked_tickets"].get(selected_day)
            
            # Show lock/unlock controls
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.write(f"**Current Status:** {'🔒 Locked' if locked_ticket_id else '✅ Available'}")
            with col2:
                if locked_ticket_id:
                    if st.button("🔓 Unlock Day", key=f"unlock_{selected_day}"):
                        if unlock_day(selected_day):
                            st.success(f"Day {selected_day} unlocked!")
                            st.rerun()
            
            # Show tickets for the location
            day_tickets = [t for t in tickets if t["location"] == location]
            if day_tickets:
                for ticket in day_tickets:
                    is_locked = ticket["ticket_id"] == locked_ticket_id
                    with st.expander(
                        f"{'🔒 ' if is_locked else ''}🎫 {ticket['ticket']} - {ticket['date']}", 
                        expanded=is_locked
                    ):
                        st.write(f"**Description:** {ticket['description']}")
                        st.write(f"**Submitted:** {ticket['submitted_at']}")
                        
                        # Lock/Archive controls
                        col1, col2 = st.columns([0.5, 0.5])
                        with col1:
                            if not is_locked and not locked_ticket_id:
                                if st.button("🔒 Lock to Day", key=f"lock_{ticket['ticket_id']}"):
                                    if lock_ticket_to_day(ticket["ticket_id"], selected_day):
                                        st.success(f"Ticket locked to {selected_day}!")
                                        st.rerun()
                        with col2:
                            if st.button("🗑️ Archive", key=f"archive_{ticket['ticket_id']}"):
                                if archive_ticket(ticket):
                                    tickets = [t for t in tickets if t['ticket_id'] != ticket['ticket_id']]
                                    with open("data/tickets.json", "w") as f:
                                        json.dump(tickets, f, indent=2)
                                    st.success("Ticket archived successfully!")
                                    st.rerun()
            else:
                st.info("No tickets for this location.")
else:
    st.info("No schedule generated. Please add some tickets to create a schedule.")

# --- Show Submitted Tickets as a Table ---
if tickets:
    st.subheader("📄 Submitted Tickets")
    
    # Add Clear Tickets section
    with st.expander("🗑️ Clear Tickets", expanded=False):
        st.write("Select time interval to clear tickets:")
        clear_option = st.selectbox(
            "Clear tickets from:",
            ["Last 24 hours", "Last 7 days", "Last 30 days", "All tickets"],
            key="clear_tickets"
        )
        
        if st.button("Clear Selected Tickets", type="primary"):
            try:
                current_time = datetime.now()
                filtered_tickets = []
                archived_tickets = []
                
                for ticket in tickets:
                    ticket_date = datetime.strptime(ticket['date'], "%Y-%m-%d")
                    days_diff = (current_time - ticket_date).days
                    
                    if clear_option == "Last 24 hours" and days_diff <= 1:
                        archived_tickets.append(ticket)
                    elif clear_option == "Last 7 days" and days_diff <= 7:
                        archived_tickets.append(ticket)
                    elif clear_option == "Last 30 days" and days_diff <= 30:
                        archived_tickets.append(ticket)
                    elif clear_option == "All tickets":
                        archived_tickets.append(ticket)
                    else:
                        filtered_tickets.append(ticket)
                
                # Archive the tickets before removing
                for ticket in archived_tickets:
                    archive_ticket(ticket)
                
                # Save the filtered tickets
                with open("data/tickets.json", "w") as f:
                    json.dump(filtered_tickets, f, indent=2)
                
                st.success(f"✅ Cleared and archived tickets from {clear_option.lower()}")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing tickets: {str(e)}")
    
    # Create a DataFrame with an index for deletion
    df = pd.DataFrame(tickets)
    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)
    
    # Add delete buttons for each ticket
    for idx, ticket in df.iterrows():
        col1, col2 = st.columns([0.95, 0.05])
        with col1:
            st.dataframe(pd.DataFrame([ticket]), hide_index=True)
        with col2:
            if st.button("🗑️", key=f"delete_{ticket['ticket_id']}"):
                try:
                    # Archive the ticket before removing
                    if archive_ticket(ticket):
                        # Convert Series to dict for removal
                        ticket_dict = ticket.to_dict()
                        tickets = [t for t in tickets if t['ticket_id'] != ticket_dict['ticket_id']]
                        with open("data/tickets.json", "w") as f:
                            json.dump(tickets, f, indent=2)
                        st.success(f"Ticket '{ticket['ticket']}' archived and deleted!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error deleting ticket: {str(e)}")
else:
    st.info("No tickets submitted yet.")
