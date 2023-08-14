"""
Dummy database backend for Django.

Django uses this if the database ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raise
ImproperlyConfigured.
"""

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.client import BaseDatabaseClient
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.backends.dummy.features import DummyDatabaseFeatures


# [TODO] complain
def complain(*args, **kwargs):
    raise ImproperlyConfigured(
        "settings.DATABASES is improperly configured. "
        "Please supply the ENGINE value. Check "
        "settings documentation for more details."
    )


# [TODO] ignore
def ignore(*args, **kwargs):
    pass


# [TODO] DatabaseOperations
class DatabaseOperations(BaseDatabaseOperations):
    quote_name = complain


# [TODO] DatabaseClient
class DatabaseClient(BaseDatabaseClient):
    runshell = complain


# [TODO] DatabaseCreation
class DatabaseCreation(BaseDatabaseCreation):
    create_test_db = ignore
    destroy_test_db = ignore


# [TODO] DatabaseIntrospection
class DatabaseIntrospection(BaseDatabaseIntrospection):
    get_table_list = complain
    get_table_description = complain
    get_relations = complain
    get_indexes = complain


# [TODO] DatabaseWrapper
class DatabaseWrapper(BaseDatabaseWrapper):
    operators = {}
    # Override the base class implementations with null
    # implementations. Anything that tries to actually
    # do something raises complain; anything that tries
    # to rollback or undo something raises ignore.
    _cursor = complain
    ensure_connection = complain
    _commit = complain
    _rollback = ignore
    _close = ignore
    _savepoint = ignore
    _savepoint_commit = complain
    _savepoint_rollback = ignore
    _set_autocommit = complain
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DummyDatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    # [TODO] DatabaseWrapper > is_usable
    def is_usable(self):
        return True