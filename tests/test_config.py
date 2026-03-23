from src.config import Settings

def test_settings_loads_from_env():
    settings = Settings()
    assert settings.timezone == "Australia/Brisbane"
    assert settings.cache_schedule_hour == 4
    assert settings.openweathermap_api_key == "test-weather-key"
    assert settings.work_address == "305 Taylor St, Wilsonton QLD 4350"
    assert settings.api_bearer_token == "test-bearer-token"
