from django.core.cache import cache

def test_cache():
    cache.set("hello", "world", 60)
    print(cache.get("hello"))
