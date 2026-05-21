import json
import hashlib
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_sync_client = None


def _get_redis_sync():
    global _redis_sync_client
    if _redis_sync_client is None:
        try:
            import redis
            from backend.config import settings
            redis_url = getattr(settings, "REDIS_URL", None)
            if redis_url:
                _redis_sync_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("[CACHE] Redis sync client connected")
        except Exception as e:
            logger.warning(f"[CACHE] Redis sync unavailable: {e}")
    return _redis_sync_client


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aredis
            from backend.config import settings
            redis_url = getattr(settings, "REDIS_URL", None)
            if redis_url:
                _redis_client = aredis.from_url(redis_url, decode_responses=True)
                logger.info("[CACHE] Redis connected")
        except Exception as e:
            logger.warning(f"[CACHE] Redis unavailable: {e}")
    return _redis_client


class MemoryCache:
    def __init__(self):
        self._cache = {}
        self._ttl = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._cache:
            if key in self._ttl and time.time() > self._ttl[key]:
                del self._cache[key]
                del self._ttl[key]
                return None
            return self._cache[key]
        return None

    def set(self, key: str, value: str, ttl: int = 300):
        self._cache[key] = value
        self._ttl[key] = time.time() + ttl


memory_cache = MemoryCache()


def cache_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{':'.join(str(a) for a in args)}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cache_sync(key: str) -> Optional[str]:
    r = _get_redis_sync()
    if r:
        try:
            return r.get(key)
        except Exception:
            pass
    return memory_cache.get(key)


def set_cache_sync(key: str, value: str, ttl: int = 300):
    r = _get_redis_sync()
    if r:
        try:
            r.set(key, value, ex=ttl)
            return
        except Exception:
            pass
    memory_cache.set(key, value, ttl)


async def get_cache(key: str) -> Optional[str]:
    r = await _get_redis()
    if r:
        try:
            return await r.get(key)
        except Exception:
            pass
    return memory_cache.get(key)


async def set_cache(key: str, value: str, ttl: int = 300):
    r = await _get_redis()
    if r:
        try:
            await r.set(key, value, ex=ttl)
            return
        except Exception:
            pass
    memory_cache.set(key, value, ttl)
