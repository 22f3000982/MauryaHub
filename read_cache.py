"""Small, disposable cache for public read data; never a source of truth."""

from collections import OrderedDict
from functools import wraps
from threading import RLock
from time import monotonic


class ReadCache:
    def __init__(self, max_entries=128, clock=monotonic):
        self._entries = OrderedDict()
        self._lock = RLock()
        self._load_locks = [RLock() for _ in range(16)]
        self._generation = 0
        self._max_entries = max_entries
        self._clock = clock

    def get_or_load(self, key, loader, ttl, cache_if=None):
        # Coalesce simultaneous misses without serializing every cache key.
        with self._load_locks[hash(key) % len(self._load_locks)]:
            with self._lock:
                entry = self._entries.get(key)
                if entry is not None and self._clock() < entry[0]:
                    self._entries.move_to_end(key)
                    return entry[1]
                self._entries.pop(key, None)
                generation = self._generation

            value = loader()  # Exceptions are never cached.
            if cache_if is not None and not cache_if(value):
                return value
            with self._lock:
                # A concurrent edit must not repopulate a cleared cache.
                if generation == self._generation:
                    self._entries[key] = (self._clock() + ttl, value)
                    self._entries.move_to_end(key)
                    while len(self._entries) > self._max_entries:
                        self._entries.popitem(last=False)
            return value

    def invalidate(self, key):
        with self._lock:
            self._generation += 1
            self._entries.pop(key, None)

    def clear(self):
        with self._lock:
            self._generation += 1
            self._entries.clear()

    def cached(self, key, ttl, cache_if=None):
        def decorate(loader):
            @wraps(loader)
            def wrapped():
                return self.get_or_load(key, loader, ttl, cache_if)
            return wrapped
        return decorate
