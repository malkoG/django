from asgiref.local import Local

from django.conf import settings as django_settings
from django.utils.functional import cached_property


# [TODO] ConnectionProxy
class ConnectionProxy:
    """Proxy for accessing a connection object's attributes."""

    # [TODO] ConnectionProxy > __init__
    def __init__(self, connections, alias):
        self.__dict__["_connections"] = connections
        self.__dict__["_alias"] = alias

    # [TODO] ConnectionProxy > __getattr__
    def __getattr__(self, item):
        return getattr(self._connections[self._alias], item)

    # [TODO] ConnectionProxy > __setattr__
    def __setattr__(self, name, value):
        return setattr(self._connections[self._alias], name, value)

    # [TODO] ConnectionProxy > __delattr__
    def __delattr__(self, name):
        return delattr(self._connections[self._alias], name)

    # [TODO] ConnectionProxy > __contains__
    def __contains__(self, key):
        return key in self._connections[self._alias]

    # [TODO] ConnectionProxy > __eq__
    def __eq__(self, other):
        return self._connections[self._alias] == other


# [TODO] ConnectionDoesNotExist
class ConnectionDoesNotExist(Exception):
    pass


# [TODO] BaseConnectionHandler
class BaseConnectionHandler:
    settings_name = None
    exception_class = ConnectionDoesNotExist
    thread_critical = False

    # [TODO] BaseConnectionHandler > __init__
    def __init__(self, settings=None):
        self._settings = settings
        self._connections = Local(self.thread_critical)

    # [TODO] BaseConnectionHandler > settings
    @cached_property
    def settings(self):
        self._settings = self.configure_settings(self._settings)
        return self._settings

    # [TODO] BaseConnectionHandler > configure_settings
    def configure_settings(self, settings):
        if settings is None:
            settings = getattr(django_settings, self.settings_name)
        return settings

    # [TODO] BaseConnectionHandler > create_connection
    def create_connection(self, alias):
        raise NotImplementedError("Subclasses must implement create_connection().")

    # [TODO] BaseConnectionHandler > __getitem__
    def __getitem__(self, alias):
        try:
            return getattr(self._connections, alias)
        except AttributeError:
            if alias not in self.settings:
                raise self.exception_class(f"The connection '{alias}' doesn't exist.")
        conn = self.create_connection(alias)
        setattr(self._connections, alias, conn)
        return conn

    # [TODO] BaseConnectionHandler > __setitem__
    def __setitem__(self, key, value):
        setattr(self._connections, key, value)

    # [TODO] BaseConnectionHandler > __delitem__
    def __delitem__(self, key):
        delattr(self._connections, key)

    # [TODO] BaseConnectionHandler > __iter__
    def __iter__(self):
        return iter(self.settings)

    # [TODO] BaseConnectionHandler > all
    def all(self, initialized_only=False):
        return [
            self[alias]
            for alias in self
            # If initialized_only is True, return only initialized connections.
            if not initialized_only or hasattr(self._connections, alias)
        ]

    # [TODO] BaseConnectionHandler > close_all
    def close_all(self):
        for conn in self.all(initialized_only=True):
            conn.close()