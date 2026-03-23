from __future__ import annotations

import logging
import re
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
import vobject

from src.config import settings

logger = logging.getLogger(__name__)

CARDDAV_BASE = "https://contacts.icloud.com"

DAV_NS = "DAV:"
CARDDAV_NS = "urn:ietf:params:xml:ns:carddav"


def _get_today_mmdd() -> str:
    return datetime.now().strftime("%m%d")


async def _discover_addressbook_url() -> str:
    """Discover the user's CardDAV addressbook URL via PROPFIND."""
    auth = (settings.icloud_username, settings.icloud_app_password)

    async with httpx.AsyncClient() as client:
        # Step 1: PROPFIND on base URL to find current-user-principal
        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:current-user-principal/>
  </d:prop>
</d:propfind>"""

        resp = await client.request(
            method="PROPFIND",
            url=f"{CARDDAV_BASE}/",
            content=propfind_body,
            headers={"Content-Type": "application/xml", "Depth": "0"},
            auth=auth,
            timeout=30.0,
        )

        if resp.status_code == 401:
            raise RuntimeError("iCloud CardDAV auth failed — check username and app-specific password")

        # Parse principal URL from response
        try:
            root = ET.fromstring(resp.text)
            href = root.find(".//{DAV:}current-user-principal/{DAV:}href")
            if href is not None and href.text:
                principal_url = href.text
            else:
                # Fallback: use username-based URL
                principal_url = f"/{settings.icloud_username}/"
        except ET.ParseError:
            principal_url = f"/{settings.icloud_username}/"

        logger.info(f"CardDAV principal URL: {principal_url}")

        # Step 2: PROPFIND on principal to find addressbook-home-set
        home_body = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <card:addressbook-home-set/>
  </d:prop>
</d:propfind>"""

        resp2 = await client.request(
            method="PROPFIND",
            url=f"{CARDDAV_BASE}{principal_url}",
            content=home_body,
            headers={"Content-Type": "application/xml", "Depth": "0"},
            auth=auth,
            timeout=30.0,
        )

        try:
            root2 = ET.fromstring(resp2.text)
            home_href = root2.find(
                ".//{urn:ietf:params:xml:ns:carddav}addressbook-home-set/{DAV:}href"
            )
            if home_href is not None and home_href.text:
                return home_href.text
        except ET.ParseError:
            pass

        # Fallback
        return f"{principal_url}carddavhome/card/"


async def _fetch_all_vcards() -> str:
    """Fetch all vCards from the discovered iCloud CardDAV addressbook."""
    addressbook_url = await _discover_addressbook_url()
    logger.info(f"CardDAV addressbook URL: {addressbook_url}")

    report_body = """<?xml version="1.0" encoding="UTF-8"?>
<card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <card:address-data/>
  </d:prop>
</card:addressbook-query>"""

    auth = (settings.icloud_username, settings.icloud_app_password)

    # The addressbook URL might be a full URL or a relative path
    if addressbook_url.startswith("http"):
        url = addressbook_url
    else:
        url = f"{CARDDAV_BASE}{addressbook_url}"

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method="REPORT",
            url=url,
            content=report_body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            auth=auth,
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

        bday_value = bday.value
        bday_clean = bday_value.replace("-", "")

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
