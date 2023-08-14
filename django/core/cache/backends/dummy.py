"Dummy cache backend"

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache


# [TODO] DummyCache
class DummyCache(BaseCache):
    # [TODO] DummyCache > __init__
    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # [TODO] DummyCache > add
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self.make_and_validate_key(key, version=version)
        return True

    # [TODO] DummyCache > get
    def get(self, key, default=None, version=None):
        self.make_and_validate_key(key, version=version)
        return default

    # [TODO] DummyCache > set
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self.make_and_validate_key(key, version=version)

    # [TODO] DummyCache > touch
    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        self.make_and_validate_key(key, version=version)
        return False

    # [TODO] DummyCache > delete
    def delete(self, key, version=None):
        self.make_and_validate_key(key, version=version)
        return False

    # [TODO] DummyCache > has_key
    def has_key(self, key, version=None):
        self.make_and_validate_key(key, version=version)
        return False

    # [TODO] DummyCache > clear
    def clear(self):
        pass