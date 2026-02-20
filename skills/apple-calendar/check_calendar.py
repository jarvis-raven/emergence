#!/usr/bin/env python3
"""
Apple Calendar Integration - Native macOS Calendar access via AppleScript

Handles both single and recurring events properly.
"""

import subprocess
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def run_applescript(script: str, timeout: int = 60) -> str:
    """Execute AppleScript and return output."""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr}")
    return result.stdout.strip()


def get_calendars() -> List[str]:
    """Get list of all calendar names."""
    script = 'tell application "Calendar" to get name of calendars'
    output = run_applescript(script)
    return [cal.strip() for cal in output.split(',')]


def get_upcoming_events(
    days: int = 2,
    calendars: Optional[List[str]] = None,
    exclude_calendars: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Get upcoming events within N days, including recurring event occurrences.
    """
    if exclude_calendars is None:
        exclude_calendars = ["Birthdays", "UK Holidays", "Siri Suggestions", "Scheduled Reminders"]
    
    exclude_list = ', '.join(f'"{c}"' for c in exclude_calendars)
    
    script = f'''
    tell application "Calendar"
        set today to current date
        set endDate to today + ({days} * days)
        set allEventsOutput to ""
        set excludeList to {{{exclude_list}}}
        set seenEvents to {{}}
        
        repeat with cal in calendars
            set calName to name of cal
            set skipCal to false
            
            repeat with excludeName in excludeList
                if calName is excludeName then
                    set skipCal to true
                    exit repeat
                end if
            end repeat
            
            if not skipCal then
                -- Get non-recurring events in range
                try
                    set eventsInRange to (every event of cal whose start date ≥ today and start date ≤ endDate)
                    repeat with anEvent in eventsInRange
                        set eventDate to start date of anEvent
                        set eventSummary to summary of anEvent
                        set isAllDay to (allday event of anEvent) as boolean
                        try
                            set eventLoc to location of anEvent
                        on error
                            set eventLoc to ""
                        end try
                        set recInfo to recurrence of anEvent
                        -- Skip if it's a recurring event (we handle those below)
                        if recInfo is "" or recInfo is missing value then
                            set eventInfo to calName & "|||" & eventSummary & "|||" & (eventDate as string) & "|||" & isAllDay & "|||" & eventLoc
                            if allEventsOutput is "" then
                                set allEventsOutput to eventInfo
                            else
                                set allEventsOutput to allEventsOutput & "###EVENTDELIM###" & eventInfo
                            end if
                        end if
                    end repeat
                end try
                
                -- Handle recurring events
                try
                    set recurringEvents to (every event of cal whose recurrence is not "")
                    repeat with anEvent in recurringEvents
                        set recInfo to recurrence of anEvent
                        if recInfo is not "" and recInfo is not missing value then
                            set eventSummary to summary of anEvent
                            set originalStart to start date of anEvent
                            set isAllDay to (allday event of anEvent) as boolean
                            try
                                set eventLoc to location of anEvent
                            on error
                                set eventLoc to ""
                            end try
                            
                            -- Weekly recurrence
                            if recInfo contains "FREQ=WEEKLY" then
                                set originalWeekday to weekday of originalStart
                                set originalHour to hours of originalStart
                                set originalMinute to minutes of originalStart
                                
                                set checkDate to today
                                repeat while checkDate ≤ endDate
                                    if weekday of checkDate = originalWeekday then
                                        set hours of checkDate to originalHour
                                        set minutes of checkDate to originalMinute
                                        set seconds of checkDate to 0
                                        
                                        if checkDate ≥ today and checkDate ≤ endDate then
                                            set eventKey to eventSummary & (checkDate as string)
                                            if eventKey is not in seenEvents then
                                                set end of seenEvents to eventKey
                                                set eventInfo to calName & "|||" & eventSummary & "|||" & (checkDate as string) & "|||" & isAllDay & "|||" & eventLoc
                                                if allEventsOutput is "" then
                                                    set allEventsOutput to eventInfo
                                                else
                                                    set allEventsOutput to allEventsOutput & "###EVENTDELIM###" & eventInfo
                                                end if
                                            end if
                                        end if
                                        exit repeat
                                    end if
                                    set checkDate to checkDate + 1 * days
                                end repeat
                            end if
                            
                            -- Daily recurrence
                            if recInfo contains "FREQ=DAILY" then
                                set originalHour to hours of originalStart
                                set originalMinute to minutes of originalStart
                                
                                set checkDate to today
                                set hours of checkDate to originalHour
                                set minutes of checkDate to originalMinute
                                set seconds of checkDate to 0
                                
                                if checkDate ≥ today then
                                    set eventKey to eventSummary & (checkDate as string)
                                    if eventKey is not in seenEvents then
                                        set end of seenEvents to eventKey
                                        set eventInfo to calName & "|||" & eventSummary & "|||" & (checkDate as string) & "|||" & isAllDay & "|||" & eventLoc
                                        if allEventsOutput is "" then
                                            set allEventsOutput to eventInfo
                                        else
                                            set allEventsOutput to allEventsOutput & "###EVENTDELIM###" & eventInfo
                                        end if
                                    end if
                                end if
                            end if
                        end if
                    end repeat
                end try
            end if
        end repeat
        
        return allEventsOutput
    end tell
    '''
    
    output = run_applescript(script, timeout=120)
    if not output:
        return []
    
    events = []
    for line in output.split('###EVENTDELIM###'):
        if not line.strip():
            continue
        parts = line.split('|||')
        if len(parts) >= 4:
            events.append({
                'calendar': parts[0],
                'summary': parts[1],
                'date_str': parts[2],
                'all_day': parts[3].strip().lower() == 'true',
                'location': parts[4] if len(parts) > 4 else ''
            })
    
    # Sort by date
    def parse_date(d):
        try:
            # "Thursday, 19 February 2026 at 18:30:00"
            return datetime.strptime(d, '%A, %d %B %Y at %H:%M:%S')
        except:
            return datetime.max
    
    events.sort(key=lambda e: parse_date(e['date_str']))
    return events


def format_event_list(events: List[Dict[str, str]], max_events: int = 10) -> str:
    """Format events for display."""
    if not events:
        return "📅 No upcoming events."
    
    lines = [f"📅 Upcoming events ({len(events)}):"]
    lines.append("")
    
    for event in events[:max_events]:
        calendar = event['calendar']
        summary = event['summary']
        date_str = event['date_str']
        location = event.get('location', '')
        
        if ' at ' in date_str:
            date_part, time_part = date_str.split(' at ')
            if ', ' in date_part:
                date_only = ', '.join(date_part.split(', ')[1:])
            else:
                date_only = date_part
            time_short = ':'.join(time_part.split(':')[:2])
            lines.append(f"• {summary}")
            lines.append(f"  📆 {date_only} at {time_short}")
        else:
            date_only = ', '.join(date_str.split(', ')[1:]) if ', ' in date_str else date_str
            lines.append(f"• {summary}")
            lines.append(f"  📆 {date_only} (all day)")
        
        if location:
            loc_short = location[:60] + '...' if len(location) > 60 else location
            lines.append(f"  📍 {loc_short}")
        
        if calendar not in ["Jarvis", "Home", "Work"]:
            lines.append(f"  [{calendar}]")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check Apple Calendar events')
    parser.add_argument('--days', type=int, default=2, help='Days ahead to check (default: 2)')
    parser.add_argument('--list-calendars', action='store_true', help='List available calendars')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.list_calendars:
        cals = get_calendars()
        print("Available calendars:")
        for cal in cals:
            print(f"  • {cal}")
        return
    
    events = get_upcoming_events(days=args.days)
    
    if args.json:
        print(json.dumps(events, indent=2))
    else:
        print(format_event_list(events))


if __name__ == '__main__':
    main()
