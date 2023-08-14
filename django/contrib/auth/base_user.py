"""
This module allows importing AbstractBaseUser even when django.contrib.auth is
not in INSTALLED_APPS.
"""
import unicodedata
import warnings

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import (
    acheck_password,
    check_password,
    is_password_usable,
    make_password,
)
from django.db import models
from django.utils.crypto import get_random_string, salted_hmac
from django.utils.deprecation import RemovedInDjango51Warning
from django.utils.translation import gettext_lazy as _


# [TODO] BaseUserManager
class BaseUserManager(models.Manager):
    # [TODO] BaseUserManager > normalize_email
    @classmethod
    def normalize_email(cls, email):
        """
        Normalize the email address by lowercasing the domain part of it.
        """
        email = email or ""
        try:
            email_name, domain_part = email.strip().rsplit("@", 1)
        except ValueError:
            pass
        else:
            email = email_name + "@" + domain_part.lower()
        return email

    # [TODO] BaseUserManager > make_random_password
    def make_random_password(
        self,
        length=10,
        allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789",
    ):
        """
        Generate a random password with the given length and given
        allowed_chars. The default value of allowed_chars does not have "I" or
        "O" or letters and digits that look similar -- just to avoid confusion.
        """
        warnings.warn(
            "BaseUserManager.make_random_password() is deprecated.",
            category=RemovedInDjango51Warning,
            stacklevel=2,
        )
        return get_random_string(length, allowed_chars)

    # [TODO] BaseUserManager > get_by_natural_key
    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})


# [TODO] AbstractBaseUser
class AbstractBaseUser(models.Model):
    password = models.CharField(_("password"), max_length=128)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)

    is_active = True

    REQUIRED_FIELDS = []

    # Stores the raw password if set_password() is called so that it can
    # be passed to password_changed() after the model is saved.
    _password = None

    # [TODO] AbstractBaseUser > Meta
    class Meta:
        abstract = True

    # [TODO] AbstractBaseUser > __str__
    def __str__(self):
        return self.get_username()

    # [TODO] AbstractBaseUser > save
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._password is not None:
            password_validation.password_changed(self._password, self)
            self._password = None

    # [TODO] AbstractBaseUser > get_username
    def get_username(self):
        """Return the username for this User."""
        return getattr(self, self.USERNAME_FIELD)

    # [TODO] AbstractBaseUser > clean
    def clean(self):
        setattr(self, self.USERNAME_FIELD, self.normalize_username(self.get_username()))

    # [TODO] AbstractBaseUser > natural_key
    def natural_key(self):
        return (self.get_username(),)

    # [TODO] AbstractBaseUser > is_anonymous
    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    # [TODO] AbstractBaseUser > is_authenticated
    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    # [TODO] AbstractBaseUser > set_password
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self._password = raw_password

    # [TODO] AbstractBaseUser > check_password
    def check_password(self, raw_password):
        """
        Return a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """

        def setter(raw_password):
            self.set_password(raw_password)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=["password"])

        return check_password(raw_password, self.password, setter)

    # [TODO] AbstractBaseUser > acheck_password
    async def acheck_password(self, raw_password):
        """See check_password()."""

        async def setter(raw_password):
            self.set_password(raw_password)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            await self.asave(update_fields=["password"])

        return await acheck_password(raw_password, self.password, setter)

    # [TODO] AbstractBaseUser > set_unusable_password
    def set_unusable_password(self):
        # Set a value that will never be a valid hash
        self.password = make_password(None)

    # [TODO] AbstractBaseUser > has_usable_password
    def has_usable_password(self):
        """
        Return False if set_unusable_password() has been called for this user.
        """
        return is_password_usable(self.password)

    # [TODO] AbstractBaseUser > get_session_auth_hash
    def get_session_auth_hash(self):
        """
        Return an HMAC of the password field.
        """
        return self._get_session_auth_hash()

    # [TODO] AbstractBaseUser > get_session_auth_fallback_hash
    def get_session_auth_fallback_hash(self):
        for fallback_secret in settings.SECRET_KEY_FALLBACKS:
            yield self._get_session_auth_hash(secret=fallback_secret)

    # [TODO] AbstractBaseUser > _get_session_auth_hash
    def _get_session_auth_hash(self, secret=None):
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            self.password,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()

    # [TODO] AbstractBaseUser > get_email_field_name
    @classmethod
    def get_email_field_name(cls):
        try:
            return cls.EMAIL_FIELD
        except AttributeError:
            return "email"

    # [TODO] AbstractBaseUser > normalize_username
    @classmethod
    def normalize_username(cls, username):
        return (
            unicodedata.normalize("NFKC", username)
            if isinstance(username, str)
            else username
        )