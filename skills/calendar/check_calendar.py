#!/usr/bin/env python3
"""
Check Dan's shared Google Calendar for upcoming events.
"""

import sys
from datetime import datetime, timedelta, timezone
import urllib.request
from icalendar import Calendar

CALENDAR_URL = "https://calendar.google.com/calendar/ical/dd23aade0f83776ddb080a692b614da92394f003323104af6eb3eaf6f0f33cab%40group.calendar.google.com/private-71ea507b5ebb837045a598be7faf31c2/basic.ics"

def fetch_calendar():
    """Fetch the ICS feed from Google Calendar."""
    try:
        with urllib.request.urlopen(CALENDAR_URL, timeout=10) as response:
            return response.read()
    except Exception as e:
        print(f"❌ Failed to fetch calendar: {e}", file=sys.stderr)
        sys.exit(1)

def parse_events(ics_data, hours_ahead=48):
    """Parse ICS data and return events in the next N hours."""
    cal = Calendar.from_ical(ics_data)
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours_ahead)
    
    events = []
    
    for component in cal.walk('VEVENT'):
        summary = str(component.get('SUMMARY', 'Untitled'))
        
        # Handle both datetime and date-only events
        dtstart = component.get('DTSTART')
        if dtstart:
            dt = dtstart.dt
            # Convert date to datetime if needed
            if not isinstance(dt, datetime):
                dt = datetime.combine(dt, datetime.min.time())
            # Make timezone-aware if needed
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Only include upcoming events
            if now <= dt <= cutoff:
                events.append({
                    'summary': summary,
                    'start': dt,
                    'description': str(component.get('DESCRIPTION', ''))
                })
    
    # Sort by start time
    events.sort(key=lambda x: x['start'])
    return events

def format_events(events):
    """Format events for display."""
    if not events:
        return "📅 No upcoming events in the next 48 hours."
    
    output = [f"📅 {len(events)} upcoming event{'s' if len(events) != 1 else ''}:\n"]
    now = datetime.now(timezone.utc)
    
    for event in events:
        start = event['start']
        delta = start - now
        hours = delta.total_seconds() / 3600
        
        # Time until event
        if hours < 1:
            time_str = "in <1 hour"
        elif hours < 24:
            time_str = f"in {int(hours)} hours"
        else:
            days = int(hours / 24)
            time_str = f"in {days} day{'s' if days != 1 else ''}"
        
        # Format datetime
        date_str = start.strftime("%a %d %b, %H:%M" if start.hour or start.minute else "%a %d %b")
        
        output.append(f"  • {event['summary']}")
        output.append(f"    {date_str} ({time_str})")
        
        if event['description'].strip():
            output.append(f"    Note: {event['description'].strip()}")
        output.append("")
    
    return "\n".join(output)

def main():
    hours = 48
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [hours_ahead]", file=sys.stderr)
            sys.exit(1)
    
    print("📡 Fetching calendar...")
    ics_data = fetch_calendar()
    
    events = parse_events(ics_data, hours_ahead=hours)
    print(format_events(events))

if __name__ == '__main__':
    main()
