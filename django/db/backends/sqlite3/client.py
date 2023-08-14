from django.db.backends.base.client import BaseDatabaseClient


# [TODO] DatabaseClient
class DatabaseClient(BaseDatabaseClient):
    executable_name = "sqlite3"

    # [TODO] DatabaseClient > settings_to_cmd_args_env
    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        args = [cls.executable_name, settings_dict["NAME"], *parameters]
        return args, None