from itertools import chain

from django.utils.inspect import func_accepts_kwargs
from django.utils.itercompat import is_iterable


# [TODO] Tags
class Tags:
    """
    Built-in tags for internal checks.
    """

    admin = "admin"
    async_support = "async_support"
    caches = "caches"
    compatibility = "compatibility"
    database = "database"
    files = "files"
    models = "models"
    security = "security"
    signals = "signals"
    sites = "sites"
    staticfiles = "staticfiles"
    templates = "templates"
    translation = "translation"
    urls = "urls"


# [TODO] CheckRegistry
class CheckRegistry:
    # [TODO] CheckRegistry > __init__
    def __init__(self):
        self.registered_checks = set()
        self.deployment_checks = set()

    # [TODO] CheckRegistry > register
    def register(self, check=None, *tags, **kwargs):
        """
        Can be used as a function or a decorator. Register given function
        `f` labeled with given `tags`. The function should receive **kwargs
        and return list of Errors and Warnings.

        Example::

            registry = CheckRegistry()
            @registry.register('mytag', 'anothertag')
            def my_check(app_configs, **kwargs):
                # ... perform checks and collect `errors` ...
                return errors
            # or
            registry.register(my_check, 'mytag', 'anothertag')
        """

        def inner(check):
            if not func_accepts_kwargs(check):
                raise TypeError(
                    "Check functions must accept keyword arguments (**kwargs)."
                )
            check.tags = tags
            checks = (
                self.deployment_checks
                if kwargs.get("deploy")
                else self.registered_checks
            )
            checks.add(check)
            return check

        if callable(check):
            return inner(check)
        else:
            if check:
                tags += (check,)
            return inner

    # [TODO] CheckRegistry > run_checks
    def run_checks(
        self,
        app_configs=None,
        tags=None,
        include_deployment_checks=False,
        databases=None,
    ):
        """
        Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        checks = self.get_checks(include_deployment_checks)

        if tags is not None:
            checks = [check for check in checks if not set(check.tags).isdisjoint(tags)]

        for check in checks:
            new_errors = check(app_configs=app_configs, databases=databases)
            if not is_iterable(new_errors):
                raise TypeError(
                    "The function %r did not return a list. All functions "
                    "registered with the checks registry must return a list." % check,
                )
            errors.extend(new_errors)
        return errors

    # [TODO] CheckRegistry > tag_exists
    def tag_exists(self, tag, include_deployment_checks=False):
        return tag in self.tags_available(include_deployment_checks)

    # [TODO] CheckRegistry > tags_available
    def tags_available(self, deployment_checks=False):
        return set(
            chain.from_iterable(
                check.tags for check in self.get_checks(deployment_checks)
            )
        )

    # [TODO] CheckRegistry > get_checks
    def get_checks(self, include_deployment_checks=False):
        checks = list(self.registered_checks)
        if include_deployment_checks:
            checks.extend(self.deployment_checks)
        return checks


registry = CheckRegistry()
register = registry.register
run_checks = registry.run_checks
tag_exists = registry.tag_exists