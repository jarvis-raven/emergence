# Apple Calendar Skill

Native macOS Calendar integration via AppleScript.

## What It Does

Provides read access to Apple Calendar events with clean Python API and CLI interface.

## Requirements

- macOS with Calendar app
- Calendar access permission granted (first run will prompt)
- Python 3

## Usage

### CLI

```bash
# Check upcoming events (default: 2 days)
python3 check_calendar.py

# Check next 7 days
python3 check_calendar.py --days 7

# List available calendars
python3 check_calendar.py --list-calendars

# Get JSON output
python3 check_calendar.py --days 14 --json
```

### Python API

```python
from check_calendar import get_upcoming_events, get_calendars, format_event_list

# Get events
events = get_upcoming_events(days=2)

# Exclude specific calendars
events = get_upcoming_events(
    days=7,
    exclude_calendars=["Birthdays", "UK Holidays"]
)

# Format for display
print(format_event_list(events))

# Get calendar list
calendars = get_calendars()
```

## Event Format

Events are returned as dictionaries:

```python
{
    'calendar': 'Jarvis',
    'summary': 'Meeting with Dan',
    'date_str': 'Monday, 24 February 2026 at 14:00:00',
    'all_day': False
}
```

## Integration with CARE Drive

Use in CARE drive satisfaction to check upcoming events:

```python
from skills.apple_calendar.check_calendar import get_upcoming_events, format_event_list

events = get_upcoming_events(days=2)
if events:
    print(format_event_list(events))
else:
    print("📅 No upcoming events in next 48 hours")
```

## Default Exclusions

The following system calendars are excluded by default:
- Birthdays
- UK Holidays  
- Siri Suggestions

## Future Enhancements

- Write support (add/modify/delete events)
- Reminder integration
- Time-based filtering (next 24 hours, today only)
- iCal export/import

## Files

- `check_calendar.py` - Main script (CLI + API)
- `SKILL.md` - This file

## Notes

This skill uses AppleScript under the hood, which requires Calendar.app permissions. The first time you run it, macOS will prompt you to grant access.

The skill intentionally uses native Calendar access rather than external APIs or ICS feeds for:
- Reliability (no network dependencies)
- Privacy (all data stays local)
- Integration (works with all Calendar sources: iCloud, Google, Exchange, etc.)
