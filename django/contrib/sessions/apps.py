from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# [TODO] SessionsConfig
class SessionsConfig(AppConfig):
    name = "django.contrib.sessions"
    verbose_name = _("Sessions")