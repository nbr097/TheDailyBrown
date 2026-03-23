from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cache_schedule_hour: int = 4
    cache_schedule_minute: int = 0
    timezone: str = "Australia/Brisbane"
    openweathermap_api_key: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_tenant_id: str = ""
    ms_email: str = ""
    ms_password: str = ""
    icloud_username: str = ""
    icloud_app_password: str = ""
    google_maps_api_key: str = ""
    work_address: str = "305 Taylor St, Wilsonton QLD 4350"
    api_bearer_token: str = ""
    dashboard_domain: str = "morning.localhost"
    cloudflare_tunnel_token: str = ""
    github_webhook_secret: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
