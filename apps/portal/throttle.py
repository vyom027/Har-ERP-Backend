"""Simple cache-backed brute-force throttle for the tiny PIN keyspace.

Uses Django's default LocMemCache (no extra config needed). Good enough for a
single-process factory deployment; swap to Redis cache if you scale out.
"""
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60  # 15 minutes


def _key(scope, ident):
    return f"throttle:{scope}:{ident}"


def is_locked(scope, ident):
    return cache.get(_key(scope, ident), 0) >= MAX_ATTEMPTS


def register_failure(scope, ident):
    key = _key(scope, ident)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCK_SECONDS)
        count = 1
    # Refresh the window so repeated failures keep the lock alive
    if count >= MAX_ATTEMPTS:
        cache.set(key, count, LOCK_SECONDS)
    return count


def reset(scope, ident):
    cache.delete(_key(scope, ident))
