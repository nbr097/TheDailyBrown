import os
import pytest

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set minimal env vars for all tests."""
    env = {
        "CACHE_SCHEDULE_HOUR": "4",
        "CACHE_SCHEDULE_MINUTE": "0",
        "TIMEZONE": "Australia/Brisbane",
        "OPENWEATHERMAP_API_KEY": "test-weather-key",
        "MS_CLIENT_ID": "test-ms-id",
        "MS_CLIENT_SECRET": "test-ms-secret",
        "MS_TENANT_ID": "test-ms-tenant",
        "ICLOUD_USERNAME": "test@icloud.com",
        "ICLOUD_APP_PASSWORD": "test-icloud-pw",
        "GOOGLE_MAPS_API_KEY": "test-gmaps-key",
        "WORK_ADDRESS": "305 Taylor St, Wilsonton QLD 4350",
        "API_BEARER_TOKEN": "test-bearer-token",
        "DASHBOARD_DOMAIN": "morning.test.com",
        "CLOUDFLARE_TUNNEL_TOKEN": "test-cf-token",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
