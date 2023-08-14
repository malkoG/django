from django.db.backends.sqlite3.client import DatabaseClient


# [TODO] SpatiaLiteClient
class SpatiaLiteClient(DatabaseClient):
    executable_name = "spatialite"