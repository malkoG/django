"""
Wrapper for loading templates from a plain Python dict.
"""

from django.template import Origin, TemplateDoesNotExist

from .base import Loader as BaseLoader


# [TODO] Loader
class Loader(BaseLoader):
    # [TODO] Loader > __init__
    def __init__(self, engine, templates_dict):
        self.templates_dict = templates_dict
        super().__init__(engine)

    # [TODO] Loader > get_contents
    def get_contents(self, origin):
        try:
            return self.templates_dict[origin.name]
        except KeyError:
            raise TemplateDoesNotExist(origin)

    # [TODO] Loader > get_template_sources
    def get_template_sources(self, template_name):
        yield Origin(
            name=template_name,
            template_name=template_name,
            loader=self,
        )