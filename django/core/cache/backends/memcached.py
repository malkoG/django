"Memcached cache backend"

import re
import time

from django.core.cache.backends.base import (
    DEFAULT_TIMEOUT,
    BaseCache,
    InvalidCacheKey,
    memcache_key_warnings,
)
from django.utils.functional import cached_property


# [TODO] BaseMemcachedCache
class BaseMemcachedCache(BaseCache):
    # [TODO] BaseMemcachedCache > __init__
    def __init__(self, server, params, library, value_not_found_exception):
        super().__init__(params)
        if isinstance(server, str):
            self._servers = re.split("[;,]", server)
        else:
            self._servers = server

        # Exception type raised by the underlying client library for a
        # nonexistent key.
        self.LibraryValueNotFoundException = value_not_found_exception

        self._lib = library
        self._class = library.Client
        self._options = params.get("OPTIONS") or {}

    # [TODO] BaseMemcachedCache > client_servers
    @property
    def client_servers(self):
        return self._servers

    # [TODO] BaseMemcachedCache > _cache
    @cached_property
    def _cache(self):
        """
        Implement transparent thread-safe access to a memcached client.
        """
        return self._class(self.client_servers, **self._options)

    # [TODO] BaseMemcachedCache > get_backend_timeout
    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        if timeout is None:
            # Using 0 in memcache sets a non-expiring timeout.
            return 0
        elif int(timeout) == 0:
            # Other cache backends treat 0 as set-and-expire. To achieve this
            # in memcache backends, a negative timeout must be passed.
            timeout = -1

        if timeout > 2592000:  # 60*60*24*30, 30 days
            # See https://github.com/memcached/memcached/wiki/Programming#expiration
            # "Expiration times can be set from 0, meaning "never expire", to
            # 30 days. Any time higher than 30 days is interpreted as a Unix
            # timestamp date. If you want to expire an object on January 1st of
            # next year, this is how you do that."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return int(timeout)

    # [TODO] BaseMemcachedCache > add
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.add(key, value, self.get_backend_timeout(timeout))

    # [TODO] BaseMemcachedCache > get
    def get(self, key, default=None, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.get(key, default)

    # [TODO] BaseMemcachedCache > set
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        if not self._cache.set(key, value, self.get_backend_timeout(timeout)):
            # Make sure the key doesn't keep its old value in case of failure
            # to set (memcached's 1MB limit).
            self._cache.delete(key)

    # [TODO] BaseMemcachedCache > touch
    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return bool(self._cache.touch(key, self.get_backend_timeout(timeout)))

    # [TODO] BaseMemcachedCache > delete
    def delete(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return bool(self._cache.delete(key))

    # [TODO] BaseMemcachedCache > get_many
    def get_many(self, keys, version=None):
        key_map = {
            self.make_and_validate_key(key, version=version): key for key in keys
        }
        ret = self._cache.get_multi(key_map.keys())
        return {key_map[k]: v for k, v in ret.items()}

    # [TODO] BaseMemcachedCache > close
    def close(self, **kwargs):
        # Many clients don't clean up connections properly.
        self._cache.disconnect_all()

    # [TODO] BaseMemcachedCache > incr
    def incr(self, key, delta=1, version=None):
        key = self.make_and_validate_key(key, version=version)
        try:
            # Memcached doesn't support negative delta.
            if delta < 0:
                val = self._cache.decr(key, -delta)
            else:
                val = self._cache.incr(key, delta)
        # Normalize an exception raised by the underlying client library to
        # ValueError in the event of a nonexistent key when calling
        # incr()/decr().
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    # [TODO] BaseMemcachedCache > set_many
    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        safe_data = {}
        original_keys = {}
        for key, value in data.items():
            safe_key = self.make_and_validate_key(key, version=version)
            safe_data[safe_key] = value
            original_keys[safe_key] = key
        failed_keys = self._cache.set_multi(
            safe_data, self.get_backend_timeout(timeout)
        )
        return [original_keys[k] for k in failed_keys]

    # [TODO] BaseMemcachedCache > delete_many
    def delete_many(self, keys, version=None):
        keys = [self.make_and_validate_key(key, version=version) for key in keys]
        self._cache.delete_multi(keys)

    # [TODO] BaseMemcachedCache > clear
    def clear(self):
        self._cache.flush_all()

    # [TODO] BaseMemcachedCache > validate_key
    def validate_key(self, key):
        for warning in memcache_key_warnings(key):
            raise InvalidCacheKey(warning)


# [TODO] PyLibMCCache
class PyLibMCCache(BaseMemcachedCache):
    "An implementation of a cache binding using pylibmc"

    # [TODO] PyLibMCCache > __init__
    def __init__(self, server, params):
        import pylibmc

        super().__init__(
            server, params, library=pylibmc, value_not_found_exception=pylibmc.NotFound
        )

    # [TODO] PyLibMCCache > client_servers
    @property
    def client_servers(self):
        output = []
        for server in self._servers:
            output.append(server.removeprefix("unix:"))
        return output

    # [TODO] PyLibMCCache > touch
    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        if timeout == 0:
            return self._cache.delete(key)
        return self._cache.touch(key, self.get_backend_timeout(timeout))

    # [TODO] PyLibMCCache > close
    def close(self, **kwargs):
        # libmemcached manages its own connections. Don't call disconnect_all()
        # as it resets the failover state and creates unnecessary reconnects.
        pass


# [TODO] PyMemcacheCache
class PyMemcacheCache(BaseMemcachedCache):
    """An implementation of a cache binding using pymemcache."""

    # [TODO] PyMemcacheCache > __init__
    def __init__(self, server, params):
        import pymemcache.serde

        super().__init__(
            server, params, library=pymemcache, value_not_found_exception=KeyError
        )
        self._class = self._lib.HashClient
        self._options = {
            "allow_unicode_keys": True,
            "default_noreply": False,
            "serde": pymemcache.serde.pickle_serde,
            **self._options,
        }