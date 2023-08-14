import logging
import string
from datetime import datetime, timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.module_loading import import_string

# session_key should not be case sensitive because some backends can store it
# on case insensitive file systems.
VALID_KEY_CHARS = string.ascii_lowercase + string.digits


# [TODO] CreateError
class CreateError(Exception):
    """
    Used internally as a consistent exception type to catch from save (see the
    docstring for SessionBase.save() for details).
    """

    pass


# [TODO] UpdateError
class UpdateError(Exception):
    """
    Occurs if Django tries to update a session that was deleted.
    """

    pass


# [TODO] SessionBase
class SessionBase:
    """
    Base class for all Session classes.
    """

    TEST_COOKIE_NAME = "testcookie"
    TEST_COOKIE_VALUE = "worked"

    __not_given = object()

    # [TODO] SessionBase > __init__
    def __init__(self, session_key=None):
        self._session_key = session_key
        self.accessed = False
        self.modified = False
        self.serializer = import_string(settings.SESSION_SERIALIZER)

    # [TODO] SessionBase > __contains__
    def __contains__(self, key):
        return key in self._session

    # [TODO] SessionBase > __getitem__
    def __getitem__(self, key):
        return self._session[key]

    # [TODO] SessionBase > __setitem__
    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    # [TODO] SessionBase > __delitem__
    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    # [TODO] SessionBase > key_salt
    @property
    def key_salt(self):
        return "django.contrib.sessions." + self.__class__.__qualname__

    # [TODO] SessionBase > get
    def get(self, key, default=None):
        return self._session.get(key, default)

    # [TODO] SessionBase > pop
    def pop(self, key, default=__not_given):
        self.modified = self.modified or key in self._session
        args = () if default is self.__not_given else (default,)
        return self._session.pop(key, *args)

    # [TODO] SessionBase > setdefault
    def setdefault(self, key, value):
        if key in self._session:
            return self._session[key]
        else:
            self.modified = True
            self._session[key] = value
            return value

    # [TODO] SessionBase > set_test_cookie
    def set_test_cookie(self):
        self[self.TEST_COOKIE_NAME] = self.TEST_COOKIE_VALUE

    # [TODO] SessionBase > test_cookie_worked
    def test_cookie_worked(self):
        return self.get(self.TEST_COOKIE_NAME) == self.TEST_COOKIE_VALUE

    # [TODO] SessionBase > delete_test_cookie
    def delete_test_cookie(self):
        del self[self.TEST_COOKIE_NAME]

    # [TODO] SessionBase > encode
    def encode(self, session_dict):
        "Return the given session dictionary serialized and encoded as a string."
        return signing.dumps(
            session_dict,
            salt=self.key_salt,
            serializer=self.serializer,
            compress=True,
        )

    # [TODO] SessionBase > decode
    def decode(self, session_data):
        try:
            return signing.loads(
                session_data, salt=self.key_salt, serializer=self.serializer
            )
        except signing.BadSignature:
            logger = logging.getLogger("django.security.SuspiciousSession")
            logger.warning("Session data corrupted")
        except Exception:
            # ValueError, unpickling exceptions. If any of these happen, just
            # return an empty dictionary (an empty session).
            pass
        return {}

    # [TODO] SessionBase > update
    def update(self, dict_):
        self._session.update(dict_)
        self.modified = True

    # [TODO] SessionBase > has_key
    def has_key(self, key):
        return key in self._session

    # [TODO] SessionBase > keys
    def keys(self):
        return self._session.keys()

    # [TODO] SessionBase > values
    def values(self):
        return self._session.values()

    # [TODO] SessionBase > items
    def items(self):
        return self._session.items()

    # [TODO] SessionBase > clear
    def clear(self):
        # To avoid unnecessary persistent storage accesses, we set up the
        # internals directly (loading data wastes time, since we are going to
        # set it to an empty dict anyway).
        self._session_cache = {}
        self.accessed = True
        self.modified = True

    # [TODO] SessionBase > is_empty
    def is_empty(self):
        "Return True when there is no session_key and the session is empty."
        try:
            return not self._session_key and not self._session_cache
        except AttributeError:
            return True

    # [TODO] SessionBase > _get_new_session_key
    def _get_new_session_key(self):
        "Return session key that isn't being used."
        while True:
            session_key = get_random_string(32, VALID_KEY_CHARS)
            if not self.exists(session_key):
                return session_key

    # [TODO] SessionBase > _get_or_create_session_key
    def _get_or_create_session_key(self):
        if self._session_key is None:
            self._session_key = self._get_new_session_key()
        return self._session_key

    # [TODO] SessionBase > _validate_session_key
    def _validate_session_key(self, key):
        """
        Key must be truthy and at least 8 characters long. 8 characters is an
        arbitrary lower bound for some minimal key security.
        """
        return key and len(key) >= 8

    # [TODO] SessionBase > _get_session_key
    def _get_session_key(self):
        return self.__session_key

    # [TODO] SessionBase > _set_session_key
    def _set_session_key(self, value):
        """
        Validate session key on assignment. Invalid values will set to None.
        """
        if self._validate_session_key(value):
            self.__session_key = value
        else:
            self.__session_key = None

    session_key = property(_get_session_key)
    _session_key = property(_get_session_key, _set_session_key)

    # [TODO] SessionBase > _get_session
    def _get_session(self, no_load=False):
        """
        Lazily load session from storage (unless "no_load" is True, when only
        an empty dict is stored) and store it in the current instance.
        """
        self.accessed = True
        try:
            return self._session_cache
        except AttributeError:
            if self.session_key is None or no_load:
                self._session_cache = {}
            else:
                self._session_cache = self.load()
        return self._session_cache

    _session = property(_get_session)

    # [TODO] SessionBase > get_session_cookie_age
    def get_session_cookie_age(self):
        return settings.SESSION_COOKIE_AGE

    # [TODO] SessionBase > get_expiry_age
    def get_expiry_age(self, **kwargs):
        """Get the number of seconds until the session expires.

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs["modification"]
        except KeyError:
            modification = timezone.now()
        # Make the difference between "expiry=None passed in kwargs" and
        # "expiry not passed in kwargs", in order to guarantee not to trigger
        # self.load() when expiry is provided.
        try:
            expiry = kwargs["expiry"]
        except KeyError:
            expiry = self.get("_session_expiry")

        if not expiry:  # Checks both None and 0 cases
            return self.get_session_cookie_age()
        if not isinstance(expiry, (datetime, str)):
            return expiry
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)
        delta = expiry - modification
        return delta.days * 86400 + delta.seconds

    # [TODO] SessionBase > get_expiry_date
    def get_expiry_date(self, **kwargs):
        """Get session the expiry date (as a datetime object).

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs["modification"]
        except KeyError:
            modification = timezone.now()
        # Same comment as in get_expiry_age
        try:
            expiry = kwargs["expiry"]
        except KeyError:
            expiry = self.get("_session_expiry")

        if isinstance(expiry, datetime):
            return expiry
        elif isinstance(expiry, str):
            return datetime.fromisoformat(expiry)
        expiry = expiry or self.get_session_cookie_age()
        return modification + timedelta(seconds=expiry)

    # [TODO] SessionBase > set_expiry
    def set_expiry(self, value):
        """
        Set a custom expiration for the session. ``value`` can be an integer,
        a Python ``datetime`` or ``timedelta`` object or ``None``.

        If ``value`` is an integer, the session will expire after that many
        seconds of inactivity. If set to ``0`` then the session will expire on
        browser close.

        If ``value`` is a ``datetime`` or ``timedelta`` object, the session
        will expire at that specific future time.

        If ``value`` is ``None``, the session uses the global session expiry
        policy.
        """
        if value is None:
            # Remove any custom expiration for this session.
            try:
                del self["_session_expiry"]
            except KeyError:
                pass
            return
        if isinstance(value, timedelta):
            value = timezone.now() + value
        if isinstance(value, datetime):
            value = value.isoformat()
        self["_session_expiry"] = value

    # [TODO] SessionBase > get_expire_at_browser_close
    def get_expire_at_browser_close(self):
        """
        Return ``True`` if the session is set to expire when the browser
        closes, and ``False`` if there's an expiry date. Use
        ``get_expiry_date()`` or ``get_expiry_age()`` to find the actual expiry
        date/age, if there is one.
        """
        if (expiry := self.get("_session_expiry")) is None:
            return settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
        return expiry == 0

    # [TODO] SessionBase > flush
    def flush(self):
        """
        Remove the current session data from the database and regenerate the
        key.
        """
        self.clear()
        self.delete()
        self._session_key = None

    # [TODO] SessionBase > cycle_key
    def cycle_key(self):
        """
        Create a new session key, while retaining the current session data.
        """
        data = self._session
        key = self.session_key
        self.create()
        self._session_cache = data
        if key:
            self.delete(key)

    # Methods that child classes must implement.

    # [TODO] SessionBase > exists
    def exists(self, session_key):
        """
        Return True if the given session_key already exists.
        """
        raise NotImplementedError(
            "subclasses of SessionBase must provide an exists() method"
        )

    # [TODO] SessionBase > create
    def create(self):
        """
        Create a new session instance. Guaranteed to create a new object with
        a unique key and will have saved the result once (with empty data)
        before the method returns.
        """
        raise NotImplementedError(
            "subclasses of SessionBase must provide a create() method"
        )

    # [TODO] SessionBase > save
    def save(self, must_create=False):
        """
        Save the session data. If 'must_create' is True, create a new session
        object (or raise CreateError). Otherwise, only update an existing
        object and don't create one (raise UpdateError if needed).
        """
        raise NotImplementedError(
            "subclasses of SessionBase must provide a save() method"
        )

    # [TODO] SessionBase > delete
    def delete(self, session_key=None):
        """
        Delete the session data under this key. If the key is None, use the
        current session key value.
        """
        raise NotImplementedError(
            "subclasses of SessionBase must provide a delete() method"
        )

    # [TODO] SessionBase > load
    def load(self):
        """
        Load the session data and return a dictionary.
        """
        raise NotImplementedError(
            "subclasses of SessionBase must provide a load() method"
        )

    # [TODO] SessionBase > clear_expired
    @classmethod
    def clear_expired(cls):
        """
        Remove expired sessions from the session store.

        If this operation isn't possible on a given backend, it should raise
        NotImplementedError. If it isn't necessary, because the backend has
        a built-in expiration mechanism, it should be a no-op.
        """
        raise NotImplementedError("This backend does not support clear_expired().")