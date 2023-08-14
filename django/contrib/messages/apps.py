from django.apps import AppConfig
from django.contrib.messages.storage import base
from django.contrib.messages.utils import get_level_tags
from django.core.signals import setting_changed
from django.utils.translation import gettext_lazy as _


# [TODO] update_level_tags
def update_level_tags(setting, **kwargs):
    if setting == "MESSAGE_TAGS":
        base.LEVEL_TAGS = get_level_tags()


# [TODO] MessagesConfig
class MessagesConfig(AppConfig):
    name = "django.contrib.messages"
    verbose_name = _("Messages")

    # [TODO] MessagesConfig > ready
    def ready(self):
        setting_changed.connect(update_level_tags)