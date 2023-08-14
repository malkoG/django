"""
This module allows importing AbstractBaseSession even
when django.contrib.sessions is not in INSTALLED_APPS.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


# [TODO] BaseSessionManager
class BaseSessionManager(models.Manager):
    # [TODO] BaseSessionManager > encode
    def encode(self, session_dict):
        """
        Return the given session dictionary serialized and encoded as a string.
        """
        session_store_class = self.model.get_session_store_class()
        return session_store_class().encode(session_dict)

    # [TODO] BaseSessionManager > save
    def save(self, session_key, session_dict, expire_date):
        s = self.model(session_key, self.encode(session_dict), expire_date)
        if session_dict:
            s.save()
        else:
            s.delete()  # Clear sessions with no data.
        return s


# [TODO] AbstractBaseSession
class AbstractBaseSession(models.Model):
    session_key = models.CharField(_("session key"), max_length=40, primary_key=True)
    session_data = models.TextField(_("session data"))
    expire_date = models.DateTimeField(_("expire date"), db_index=True)

    objects = BaseSessionManager()

    # [TODO] AbstractBaseSession > Meta
    class Meta:
        abstract = True
        verbose_name = _("session")
        verbose_name_plural = _("sessions")

    # [TODO] AbstractBaseSession > __str__
    def __str__(self):
        return self.session_key

    # [TODO] AbstractBaseSession > get_session_store_class
    @classmethod
    def get_session_store_class(cls):
        raise NotImplementedError

    # [TODO] AbstractBaseSession > get_decoded
    def get_decoded(self):
        session_store_class = self.get_session_store_class()
        return session_store_class().decode(self.session_data)