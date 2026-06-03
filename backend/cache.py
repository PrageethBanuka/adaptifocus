"""Caching layer — Redis when available, in-memory dict fallback.

Resilient design: if Redis is unreachable (e.g. Upstash database deleted),
all cache operations gracefully degrade — they never crash the caller.
After repeated failures, the cache automatically falls back to in-memory mode.

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


# ── In-Memory Fallback ───────────────────────────────────────────────────────

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


# ── Resilient Redis Cache ────────────────────────────────────────────────────

_MAX_CONSECUTIVE_FAILURES = 5  # After this many failures, fall back permanently


class _RedisCache:
    """Async Redis cache wrapper with circuit-breaker pattern.

    If Redis becomes unreachable (e.g. database deleted, network issue),
    all methods return gracefully (None / no-op) instead of raising.
    After _MAX_CONSECUTIVE_FAILURES consecutive errors, the cache permanently
    degrades to in-memory mode for the lifetime of the process.
    """

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._failure_count = 0
        self._degraded = False
        self._fallback = _MemoryCache()

    def _record_success(self) -> None:
        self._failure_count = 0

    def _record_failure(self, operation: str, error: Exception) -> None:
        self._failure_count += 1
        print(f"[Cache] Redis {operation} failed ({self._failure_count}/{_MAX_CONSECUTIVE_FAILURES}): {error}")
        if self._failure_count >= _MAX_CONSECUTIVE_FAILURES:
            self._degraded = True
            print(f"[Cache] ⚠️  Too many Redis failures — permanently falling back to In-Memory cache.")
            print(f"[Cache]    This usually means the Redis/Upstash database was deleted or is unreachable.")
            print(f"[Cache]    Fix: remove REDIS_URL env var, or create a new Upstash database.")

    async def get(self, key: str) -> Optional[Any]:
        if self._degraded:
            return await self._fallback.get(key)
        try:
            raw = await self._redis.get(key)
            self._record_success()
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            self._record_failure("GET", e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        if self._degraded:
            return await self._fallback.set(key, value, ttl)
        try:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl)
            self._record_success()
        except Exception as e:
            self._record_failure("SET", e)

    async def invalidate(self, key: str) -> None:
        if self._degraded:
            return await self._fallback.invalidate(key)
        try:
            await self._redis.delete(key)
            self._record_success()
        except Exception as e:
            self._record_failure("DELETE", e)

    async def invalidate_pattern(self, pattern: str) -> None:
        if self._degraded:
            return await self._fallback.invalidate_pattern(pattern)
        try:
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
            self._record_success()
        except Exception as e:
            self._record_failure("SCAN/DELETE", e)


# ── Factory ──────────────────────────────────────────────────────────────────

def _create_cache():
    """Factory: use Redis if REDIS_URL is set, else in-memory.

    Note: redis.asyncio.from_url() is lazy — it doesn't actually connect
    until the first command. So even a deleted database will pass init.
    The circuit-breaker in _RedisCache handles runtime failures gracefully.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            print(f"[Cache] Attempting to connect to Redis...")
            instance = _RedisCache(redis_url)
            print(f"[Cache] Redis cache initialized (connection will be verified on first use).")
            return instance
        except Exception as e:
            print(f"[Cache] Redis initialization failed: {e}")
            if "rediss://" not in redis_url and "upstash.io" in redis_url:
                print(f"[Cache] HINT: Upstash usually requires 'rediss://' (SSL) instead of 'redis://'.")
            print(f"[Cache] Falling back to In-Memory cache.")
    else:
        print(f"[Cache] REDIS_URL not found. Using In-Memory fallback.")
    return _MemoryCache()


cache = _create_cache()
