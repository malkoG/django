import os
import subprocess


# [TODO] BaseDatabaseClient
class BaseDatabaseClient:
    """Encapsulate backend-specific methods for opening a client shell."""

    # This should be a string representing the name of the executable
    # (e.g., "psql"). Subclasses must override this.
    executable_name = None

    # [TODO] BaseDatabaseClient > __init__
    def __init__(self, connection):
        # connection is an instance of BaseDatabaseWrapper.
        self.connection = connection

    # [TODO] BaseDatabaseClient > settings_to_cmd_args_env
    @classmethod
    def settings_to_cmd_args_env(cls, settings_dict, parameters):
        raise NotImplementedError(
            "subclasses of BaseDatabaseClient must provide a "
            "settings_to_cmd_args_env() method or override a runshell()."
        )

    # [TODO] BaseDatabaseClient > runshell
    def runshell(self, parameters):
        args, env = self.settings_to_cmd_args_env(
            self.connection.settings_dict, parameters
        )
        env = {**os.environ, **env} if env else None
        subprocess.run(args, env=env, check=True)