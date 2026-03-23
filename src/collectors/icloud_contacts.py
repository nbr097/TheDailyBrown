from __future__ import annotations

import re
from datetime import datetime

import httpx
import vobject

from src.config import settings

CARDDAV_URL = "https://contacts.icloud.com"


def _get_today_mmdd() -> str:
    """Return today's date as a 'MMDD' string."""
    return datetime.now().strftime("%m%d")


async def _fetch_all_vcards() -> str:
    """Fetch all vCards from iCloud CardDAV using a REPORT request."""
    body = """<?xml version="1.0" encoding="UTF-8"?>
<card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <card:address-data/>
  </d:prop>
</card:addressbook-query>"""

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method="REPORT",
            url=f"{CARDDAV_URL}/",
            content=body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            auth=(settings.icloud_username, settings.icloud_app_password),
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.text


async def fetch_todays_birthdays() -> list[dict]:
    """Parse vCards and return contacts whose birthday is today."""
    raw_xml = await _fetch_all_vcards()
    today_mmdd = _get_today_mmdd()

    # Extract vCard blocks from the XML response
    vcard_pattern = re.compile(r"BEGIN:VCARD.*?END:VCARD", re.DOTALL)
    vcard_texts = vcard_pattern.findall(raw_xml)

    birthdays: list[dict] = []

    for vcard_text in vcard_texts:
        try:
            card = vobject.readOne(vcard_text)
        except Exception:
            continue

        bday = getattr(card, "bday", None)
        if bday is None:
            continue

        bday_value = bday.value  # e.g. "19900323" or "1990-03-23"
        # Normalize: strip dashes for comparison
        bday_clean = bday_value.replace("-", "")

        # Last 4 chars = MMDD
        if len(bday_clean) >= 8:
            bday_mmdd = bday_clean[4:8]
        else:
            continue

        if bday_mmdd == today_mmdd:
            name = getattr(card, "fn", None)
            display_name = name.value if name else "Unknown"
            birthdays.append({
                "name": display_name,
                "birthday": bday_value,
                "source": "personal",
            })

    return birthdays
