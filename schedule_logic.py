import json
from collections import defaultdict

def load_data():
    # Load all necessary data files
    with open('data/tickets.json') as f:
        tickets = json.load(f)
    with open('config/default_schedule.json') as f:
        default_schedule = json.load(f)
    with open('data/locked_tickets.json') as f:
        locked_tickets = json.load(f)
    return tickets, default_schedule, locked_tickets

def get_schedule(tickets, default_schedule, locked_tickets):
    # Count number of tickets per location
    location_counts = defaultdict(int)
    locked_days = {}
    
    # Process locked tickets first
    for day, ticket_id in locked_tickets['locked_tickets'].items():
        if ticket_id:
            # Find the ticket and its location
            ticket = next((t for t in tickets if t['ticket_id'] == ticket_id), None)
            if ticket:
                location_counts[ticket['location']] += 1
                locked_days[day] = ticket['location']

    # Count remaining tickets
    for ticket in tickets:
        location = ticket.get("location")
        if location and not any(ticket['ticket_id'] == tid for tid in locked_tickets['locked_tickets'].values() if tid):
            location_counts[location] += 1

    # Sort locations by ticket volume (descending)
    sorted_locations = sorted(
        location_counts.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    # Create schedule starting with locked days
    new_schedule = locked_days.copy()
    
    # Fill in remaining days with high-priority locations
    available_days = [day for day in default_schedule.keys() if day not in locked_days]
    available_locations = [loc for loc, _ in sorted_locations if loc not in locked_days.values()]
    
    for day, location in zip(available_days, available_locations):
        new_schedule[day] = location

    return new_schedule

