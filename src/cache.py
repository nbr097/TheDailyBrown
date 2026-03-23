import time
from typing import Any, Optional

class TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    @staticmethod
    def coord_key(prefix: str, lat: float, lon: float) -> str:
        return f"{prefix}:{round(lat, 1)}:{round(lon, 1)}"

location_cache = TTLCache(ttl_seconds=600)
