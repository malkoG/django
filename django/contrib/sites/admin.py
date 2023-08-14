from django.contrib import admin
from django.contrib.sites.models import Site


# [TODO] SiteAdmin
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "name")
    search_fields = ("domain", "name")