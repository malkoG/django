from importlib import import_module
from pkgutil import walk_packages

from django.apps import apps
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.context import make_context
from django.template.engine import Engine
from django.template.library import InvalidTemplateLibrary

from .base import BaseEngine


# [TODO] DjangoTemplates
class DjangoTemplates(BaseEngine):
    app_dirname = "templates"

    # [TODO] DjangoTemplates > __init__
    def __init__(self, params):
        params = params.copy()
        options = params.pop("OPTIONS").copy()
        options.setdefault("autoescape", True)
        options.setdefault("debug", settings.DEBUG)
        options.setdefault("file_charset", "utf-8")
        libraries = options.get("libraries", {})
        options["libraries"] = self.get_templatetag_libraries(libraries)
        super().__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    # [TODO] DjangoTemplates > from_string
    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    # [TODO] DjangoTemplates > get_template
    def get_template(self, template_name):
        try:
            return Template(self.engine.get_template(template_name), self)
        except TemplateDoesNotExist as exc:
            reraise(exc, self)

    # [TODO] DjangoTemplates > get_templatetag_libraries
    def get_templatetag_libraries(self, custom_libraries):
        """
        Return a collation of template tag libraries from installed
        applications and the supplied custom_libraries argument.
        """
        libraries = get_installed_libraries()
        libraries.update(custom_libraries)
        return libraries


# [TODO] Template
class Template:
    # [TODO] Template > __init__
    def __init__(self, template, backend):
        self.template = template
        self.backend = backend

    # [TODO] Template > origin
    @property
    def origin(self):
        return self.template.origin

    # [TODO] Template > render
    def render(self, context=None, request=None):
        context = make_context(
            context, request, autoescape=self.backend.engine.autoescape
        )
        try:
            return self.template.render(context)
        except TemplateDoesNotExist as exc:
            reraise(exc, self.backend)


# [TODO] copy_exception
def copy_exception(exc, backend=None):
    """
    Create a new TemplateDoesNotExist. Preserve its declared attributes and
    template debug data but discard __traceback__, __context__, and __cause__
    to make this object suitable for keeping around (in a cache, for example).
    """
    backend = backend or exc.backend
    new = exc.__class__(*exc.args, tried=exc.tried, backend=backend, chain=exc.chain)
    if hasattr(exc, "template_debug"):
        new.template_debug = exc.template_debug
    return new


# [TODO] reraise
def reraise(exc, backend):
    """
    Reraise TemplateDoesNotExist while maintaining template debug information.
    """
    new = copy_exception(exc, backend)
    raise new from exc


# [TODO] get_template_tag_modules
def get_template_tag_modules():
    """
    Yield (module_name, module_path) pairs for all installed template tag
    libraries.
    """
    candidates = ["django.templatetags"]
    candidates.extend(
        f"{app_config.name}.templatetags" for app_config in apps.get_app_configs()
    )

    for candidate in candidates:
        try:
            pkg = import_module(candidate)
        except ImportError:
            # No templatetags package defined. This is safe to ignore.
            continue

        if hasattr(pkg, "__path__"):
            for name in get_package_libraries(pkg):
                yield name.removeprefix(candidate).lstrip("."), name


# [TODO] get_installed_libraries
def get_installed_libraries():
    """
    Return the built-in template tag libraries and those from installed
    applications. Libraries are stored in a dictionary where keys are the
    individual module names, not the full module paths. Example:
    django.templatetags.i18n is stored as i18n.
    """
    return {
        module_name: full_name for module_name, full_name in get_template_tag_modules()
    }


# [TODO] get_package_libraries
def get_package_libraries(pkg):
    """
    Recursively yield template tag libraries defined in submodules of a
    package.
    """
    for entry in walk_packages(pkg.__path__, pkg.__name__ + "."):
        try:
            module = import_module(entry[1])
        except ImportError as e:
            raise InvalidTemplateLibrary(
                "Invalid template library specified. ImportError raised when "
                "trying to load '%s': %s" % (entry[1], e)
            ) from e

        if hasattr(module, "register"):
            yield entry[1]