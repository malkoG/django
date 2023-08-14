import string

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.http.request import split_domain_port
from django.utils.translation import gettext_lazy as _

SITE_CACHE = {}


# [TODO] _simple_domain_name_validator
def _simple_domain_name_validator(value):
    """
    Validate that the given value contains no whitespaces to prevent common
    typos.
    """
    checks = ((s in value) for s in string.whitespace)
    if any(checks):
        raise ValidationError(
            _("The domain name cannot contain any spaces or tabs."),
            code="invalid",
        )


# [TODO] SiteManager
class SiteManager(models.Manager):
    use_in_migrations = True

    # [TODO] SiteManager > _get_site_by_id
    def _get_site_by_id(self, site_id):
        if site_id not in SITE_CACHE:
            site = self.get(pk=site_id)
            SITE_CACHE[site_id] = site
        return SITE_CACHE[site_id]

    # [TODO] SiteManager > _get_site_by_request
    def _get_site_by_request(self, request):
        host = request.get_host()
        try:
            # First attempt to look up the site by host with or without port.
            if host not in SITE_CACHE:
                SITE_CACHE[host] = self.get(domain__iexact=host)
            return SITE_CACHE[host]
        except Site.DoesNotExist:
            # Fallback to looking up site after stripping port from the host.
            domain, port = split_domain_port(host)
            if domain not in SITE_CACHE:
                SITE_CACHE[domain] = self.get(domain__iexact=domain)
            return SITE_CACHE[domain]

    # [TODO] SiteManager > get_current
    def get_current(self, request=None):
        """
        Return the current Site based on the SITE_ID in the project's settings.
        If SITE_ID isn't defined, return the site with domain matching
        request.get_host(). The ``Site`` object is cached the first time it's
        retrieved from the database.
        """
        from django.conf import settings

        if getattr(settings, "SITE_ID", ""):
            site_id = settings.SITE_ID
            return self._get_site_by_id(site_id)
        elif request:
            return self._get_site_by_request(request)

        raise ImproperlyConfigured(
            'You\'re using the Django "sites framework" without having '
            "set the SITE_ID setting. Create a site in your database and "
            "set the SITE_ID setting or pass a request to "
            "Site.objects.get_current() to fix this error."
        )

    # [TODO] SiteManager > clear_cache
    def clear_cache(self):
        """Clear the ``Site`` object cache."""
        global SITE_CACHE
        SITE_CACHE = {}

    # [TODO] SiteManager > get_by_natural_key
    def get_by_natural_key(self, domain):
        return self.get(domain=domain)


# [TODO] Site
class Site(models.Model):
    domain = models.CharField(
        _("domain name"),
        max_length=100,
        validators=[_simple_domain_name_validator],
        unique=True,
    )
    name = models.CharField(_("display name"), max_length=50)

    objects = SiteManager()

    # [TODO] Site > Meta
    class Meta:
        db_table = "django_site"
        verbose_name = _("site")
        verbose_name_plural = _("sites")
        ordering = ["domain"]

    # [TODO] Site > __str__
    def __str__(self):
        return self.domain

    # [TODO] Site > natural_key
    def natural_key(self):
        return (self.domain,)


# [TODO] clear_site_cache
def clear_site_cache(sender, **kwargs):
    """
    Clear the cache (if primed) each time a site is saved or deleted.
    """
    instance = kwargs["instance"]
    using = kwargs["using"]
    try:
        del SITE_CACHE[instance.pk]
    except KeyError:
        pass
    try:
        del SITE_CACHE[Site.objects.using(using).get(pk=instance.pk).domain]
    except (KeyError, Site.DoesNotExist):
        pass


pre_save.connect(clear_site_cache, sender=Site)
pre_delete.connect(clear_site_cache, sender=Site)