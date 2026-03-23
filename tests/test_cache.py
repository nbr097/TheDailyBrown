import time
from src.cache import TTLCache

def test_cache_set_and_get():
    cache = TTLCache(ttl_seconds=60)
    cache.set("weather::-27.6:151.9", {"temp": 22})
    assert cache.get("weather::-27.6:151.9") == {"temp": 22}

def test_cache_expired():
    cache = TTLCache(ttl_seconds=0.1)
    cache.set("key", "value")
    time.sleep(0.2)
    assert cache.get("key") is None

def test_cache_rounds_coordinates():
    cache = TTLCache(ttl_seconds=60)
    key1 = TTLCache.coord_key("weather", -27.5712, 151.9534)
    key2 = TTLCache.coord_key("weather", -27.5748, 151.9501)
    assert key1 == key2
