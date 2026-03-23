from __future__ import annotations

from datetime import datetime, timedelta

import caldav

from src.config import settings


async def fetch_icloud_calendar() -> list[dict]:
    """Fetch today's events from all iCloud calendars via CalDAV."""
    client = caldav.DAVClient(
        url="https://caldav.icloud.com/",
        username=settings.icloud_username,
        password=settings.icloud_app_password,
    )

    principal = client.principal()
    calendars = principal.calendars()

    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    events: list[dict] = []

    for cal in calendars:
        results = cal.search(
            start=start_of_day,
            end=end_of_day,
            event=True,
            expand=True,
        )
        for item in results:
            vevent = item.vobject_instance.vevent
            contents = vevent.contents

            location = ""
            if "location" in contents:
                location = contents["location"][0].value

            event = {
                "subject": vevent.summary.value,
                "start": vevent.dtstart.value.isoformat(),
                "end": vevent.dtend.value.isoformat(),
                "location": location,
                "teams_link": None,
                "source": "personal",
            }
            events.append(event)

    return events
