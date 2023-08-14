"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages.
"""

from django.template.utils import get_app_template_dirs

from .filesystem import Loader as FilesystemLoader


# [TODO] Loader
class Loader(FilesystemLoader):
    # [TODO] Loader > get_dirs
    def get_dirs(self):
        return get_app_template_dirs("templates")