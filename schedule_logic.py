import json
from collections import defaultdict

def load_data():
    # Load all necessary data files
    with open('data/tickets.json') as f:
        tickets = json.load(f)
    with open('config/default_schedule.json') as f:
        default_schedule = json.load(f)
    with open('data/blocked_days.json') as f:
        blocked_days = json.load(f)
    return tickets, default_schedule, blocked_days

def get_schedule(tickets, default_schedule, blocked_days):
    # Count number of tickets per location
    location_counts = defaultdict(int)
    for ticket in tickets:
        location = ticket.get("location")
        if location:
            location_counts[location] += 1

    # Remove blocked days from schedule
    available_days = {
        day: location for day, location in default_schedule.items()
        if day not in blocked_days
    }

    # Sort locations by ticket volume (descending)
    sorted_locations = sorted(
        location_counts, key=location_counts.get, reverse=True
    )

    # Assign locations to available days by priority
    new_schedule = {}
    for day, location in zip(available_days.keys(), sorted_locations):
        new_schedule[day] = location

    return new_schedule

