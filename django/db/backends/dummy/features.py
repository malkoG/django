from django.db.backends.base.features import BaseDatabaseFeatures


# [TODO] DummyDatabaseFeatures
class DummyDatabaseFeatures(BaseDatabaseFeatures):
    supports_transactions = False
    uses_savepoints = False