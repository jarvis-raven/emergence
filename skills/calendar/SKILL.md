---
name: calendar
description: Check Dan's shared Google Calendar for upcoming events
metadata: { "openclaw": { "emoji": "📅" } }
---

# Calendar Integration

Access to Dan's "Jarvis" calendar via Google Calendar ICS feed.

## Usage

Check next 48 hours (default):
```bash
python3 check_calendar.py
```

Check next N hours:
```bash
python3 check_calendar.py 24   # next 24 hours
python3 check_calendar.py 72   # next 3 days
```

## What This Calendar Contains

Dan controls what goes here - this is explicitly for events he wants me to know about:
- Appointments worth reminding about
- Events needing prep
- Deadlines that matter
- Anything where advance notice is helpful

**Not his full calendar** - just the shared "Jarvis" calendar.

## Output Format

```
📅 2 upcoming events:

  • Meeting with Client
    Wed 19 Feb, 14:00 (in 2 days)
    Note: Prepare slides

  • Dentist Appointment  
    Thu 20 Feb, 09:30 (in 2 days)
```

## Privacy

- Feed URL is private (includes secret token)
- Dan controls what events are shared
- I only see what's in the "Jarvis" calendar, not his full schedule

## Integration Points

Used by:
- CARE drive (check for upcoming appointments)
- SOCIAL drive (ground in time, know what's coming)

## Calendar URL

Stored in script (check_calendar.py). If URL changes, update the `CALENDAR_URL` constant.
