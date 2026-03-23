import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.collectors.icloud_contacts import fetch_todays_birthdays

MOCK_VCARD_RESPONSE = """<multistatus>
<response><propstat><prop><card:address-data>BEGIN:VCARD
VERSION:3.0
FN:Jane Smith
BDAY:19900323
END:VCARD</card:address-data></prop></propstat></response>
<response><propstat><prop><card:address-data>BEGIN:VCARD
VERSION:3.0
FN:John Doe
BDAY:19851225
END:VCARD</card:address-data></prop></propstat></response>
</multistatus>"""

@pytest.mark.asyncio
async def test_fetch_todays_birthdays(monkeypatch):
    import datetime
    mock_now = MagicMock()
    mock_now.strftime.return_value = "0323"

    with patch("src.collectors.icloud_contacts._fetch_all_vcards", new_callable=AsyncMock, return_value=MOCK_VCARD_RESPONSE):
        with patch("src.collectors.icloud_contacts._get_today_mmdd", return_value="0323"):
            result = await fetch_todays_birthdays()

    assert len(result) == 1
    assert result[0]["name"] == "Jane Smith"
