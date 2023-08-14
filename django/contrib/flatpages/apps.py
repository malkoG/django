from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# [TODO] FlatPagesConfig
class FlatPagesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "django.contrib.flatpages"
    verbose_name = _("Flat Pages")