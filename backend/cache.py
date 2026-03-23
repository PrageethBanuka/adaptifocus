"""Caching layer — Redis when available, in-memory dict fallback.

Usage:
    from cache import cache
    await cache.set("key", data, ttl=60)
    result = await cache.get("key")
    await cache.invalidate("key")
    await cache.invalidate_pattern("analytics:user:42:*")
"""

from __future__ import annotations

import json
import time
import os
from typing import Any, Optional


class _MemoryCache:
    """Simple in-memory cache with TTL. Used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        expires_at = time.time() + ttl if ttl > 0 else 0
        self._store[key] = (value, expires_at)

    async def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    async def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern (e.g. 'analytics:user:42:*')."""
        prefix = pattern.rstrip("*")
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]


class _RedisCache:
    """Async Redis cache wrapper."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        await self._redis.set(key, json.dumps(value, default=str), ex=ttl)

    async def invalidate(self, key: str) -> None:
        await self._redis.delete(key)

    async def invalidate_pattern(self, pattern: str) -> None:
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)


def _create_cache():
    """Factory: use Redis if REDIS_URL is set, else in-memory."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            print(f"[Cache] Attempting to connect to Redis...")
            instance = _RedisCache(redis_url)
            print(f"[Cache] Connected to Redis successfully.")
            return instance
        except Exception as e:
            print(f"[Cache] Redis connection failed: {e}")
            if "rediss://" not in redis_url and "upstash.io" in redis_url:
                print(f"[Cache] HINT: Upstash usually requires 'rediss://' (SSL) instead of 'redis://'.")
            print(f"[Cache] Falling back to In-Memory cache.")
    else:
        print(f"[Cache] REDIS_URL not found. Using In-Memory fallback.")
    return _MemoryCache()


cache = _create_cache()
