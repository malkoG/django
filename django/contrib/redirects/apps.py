from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# [TODO] RedirectsConfig
class RedirectsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "django.contrib.redirects"
    verbose_name = _("Redirects")