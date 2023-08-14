import json
from collections import UserList

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.renderers import get_default_renderer
from django.utils import timezone
from django.utils.html import escape, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


# [TODO] pretty_name
def pretty_name(name):
    """Convert 'first_name' to 'First name'."""
    if not name:
        return ""
    return name.replace("_", " ").capitalize()


# [TODO] flatatt
def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs. In the case of a boolean value, the key will appear
    without a value. It is assumed that the keys do not need to be
    XML-escaped. If the passed dictionary is empty, then return an empty
    string.

    The result is passed through 'mark_safe' (by way of 'format_html_join').
    """
    key_value_attrs = []
    boolean_attrs = []
    for attr, value in attrs.items():
        if isinstance(value, bool):
            if value:
                boolean_attrs.append((attr,))
        elif value is not None:
            key_value_attrs.append((attr, value))

    return format_html_join("", ' {}="{}"', sorted(key_value_attrs)) + format_html_join(
        "", " {}", sorted(boolean_attrs)
    )


# [TODO] RenderableMixin
class RenderableMixin:
    # [TODO] RenderableMixin > get_context
    def get_context(self):
        raise NotImplementedError(
            "Subclasses of RenderableMixin must provide a get_context() method."
        )

    # [TODO] RenderableMixin > render
    def render(self, template_name=None, context=None, renderer=None):
        renderer = renderer or self.renderer
        template = template_name or self.template_name
        context = context or self.get_context()
        return mark_safe(renderer.render(template, context))

    __str__ = render
    __html__ = render


# [TODO] RenderableFieldMixin
class RenderableFieldMixin(RenderableMixin):
    # [TODO] RenderableFieldMixin > as_field_group
    def as_field_group(self):
        return self.render()

    # [TODO] RenderableFieldMixin > as_hidden
    def as_hidden(self):
        raise NotImplementedError(
            "Subclasses of RenderableFieldMixin must provide an as_hidden() method."
        )

    # [TODO] RenderableFieldMixin > as_widget
    def as_widget(self):
        raise NotImplementedError(
            "Subclasses of RenderableFieldMixin must provide an as_widget() method."
        )

    # [TODO] RenderableFieldMixin > __str__
    def __str__(self):
        """Render this field as an HTML widget."""
        if self.field.show_hidden_initial:
            return self.as_widget() + self.as_hidden(only_initial=True)
        return self.as_widget()

    __html__ = __str__


# [TODO] RenderableFormMixin
class RenderableFormMixin(RenderableMixin):
    # [TODO] RenderableFormMixin > as_p
    def as_p(self):
        """Render as <p> elements."""
        return self.render(self.template_name_p)

    # [TODO] RenderableFormMixin > as_table
    def as_table(self):
        """Render as <tr> elements excluding the surrounding <table> tag."""
        return self.render(self.template_name_table)

    # [TODO] RenderableFormMixin > as_ul
    def as_ul(self):
        """Render as <li> elements excluding the surrounding <ul> tag."""
        return self.render(self.template_name_ul)

    # [TODO] RenderableFormMixin > as_div
    def as_div(self):
        """Render as <div> elements."""
        return self.render(self.template_name_div)


# [TODO] RenderableErrorMixin
class RenderableErrorMixin(RenderableMixin):
    # [TODO] RenderableErrorMixin > as_json
    def as_json(self, escape_html=False):
        return json.dumps(self.get_json_data(escape_html))

    # [TODO] RenderableErrorMixin > as_text
    def as_text(self):
        return self.render(self.template_name_text)

    # [TODO] RenderableErrorMixin > as_ul
    def as_ul(self):
        return self.render(self.template_name_ul)


# [TODO] ErrorDict
class ErrorDict(dict, RenderableErrorMixin):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """

    template_name = "django/forms/errors/dict/default.html"
    template_name_text = "django/forms/errors/dict/text.txt"
    template_name_ul = "django/forms/errors/dict/ul.html"

    # [TODO] ErrorDict > __init__
    def __init__(self, *args, renderer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.renderer = renderer or get_default_renderer()

    # [TODO] ErrorDict > as_data
    def as_data(self):
        return {f: e.as_data() for f, e in self.items()}

    # [TODO] ErrorDict > get_json_data
    def get_json_data(self, escape_html=False):
        return {f: e.get_json_data(escape_html) for f, e in self.items()}

    # [TODO] ErrorDict > get_context
    def get_context(self):
        return {
            "errors": self.items(),
            "error_class": "errorlist",
        }


# [TODO] ErrorList
class ErrorList(UserList, list, RenderableErrorMixin):
    """
    A collection of errors that knows how to display itself in various formats.
    """

    template_name = "django/forms/errors/list/default.html"
    template_name_text = "django/forms/errors/list/text.txt"
    template_name_ul = "django/forms/errors/list/ul.html"

    # [TODO] ErrorList > __init__
    def __init__(self, initlist=None, error_class=None, renderer=None):
        super().__init__(initlist)

        if error_class is None:
            self.error_class = "errorlist"
        else:
            self.error_class = "errorlist {}".format(error_class)
        self.renderer = renderer or get_default_renderer()

    # [TODO] ErrorList > as_data
    def as_data(self):
        return ValidationError(self.data).error_list

    # [TODO] ErrorList > copy
    def copy(self):
        copy = super().copy()
        copy.error_class = self.error_class
        return copy

    # [TODO] ErrorList > get_json_data
    def get_json_data(self, escape_html=False):
        errors = []
        for error in self.as_data():
            message = next(iter(error))
            errors.append(
                {
                    "message": escape(message) if escape_html else message,
                    "code": error.code or "",
                }
            )
        return errors

    # [TODO] ErrorList > get_context
    def get_context(self):
        return {
            "errors": self,
            "error_class": self.error_class,
        }

    # [TODO] ErrorList > __repr__
    def __repr__(self):
        return repr(list(self))

    # [TODO] ErrorList > __contains__
    def __contains__(self, item):
        return item in list(self)

    # [TODO] ErrorList > __eq__
    def __eq__(self, other):
        return list(self) == other

    # [TODO] ErrorList > __getitem__
    def __getitem__(self, i):
        error = self.data[i]
        if isinstance(error, ValidationError):
            return next(iter(error))
        return error

    # [TODO] ErrorList > __reduce_ex__
    def __reduce_ex__(self, *args, **kwargs):
        # The `list` reduce function returns an iterator as the fourth element
        # that is normally used for repopulating. Since we only inherit from
        # `list` for `isinstance` backward compatibility (Refs #17413) we
        # nullify this iterator as it would otherwise result in duplicate
        # entries. (Refs #23594)
        info = super(UserList, self).__reduce_ex__(*args, **kwargs)
        return info[:3] + (None, None)


# Utilities for time zone support in DateTimeField et al.


# [TODO] from_current_timezone
def from_current_timezone(value):
    """
    When time zone support is enabled, convert naive datetimes
    entered in the current time zone to aware datetimes.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        current_timezone = timezone.get_current_timezone()
        try:
            if timezone._datetime_ambiguous_or_imaginary(value, current_timezone):
                raise ValueError("Ambiguous or non-existent time.")
            return timezone.make_aware(value, current_timezone)
        except Exception as exc:
            raise ValidationError(
                _(
                    "%(datetime)s couldn’t be interpreted "
                    "in time zone %(current_timezone)s; it "
                    "may be ambiguous or it may not exist."
                ),
                code="ambiguous_timezone",
                params={"datetime": value, "current_timezone": current_timezone},
            ) from exc
    return value


# [TODO] to_current_timezone
def to_current_timezone(value):
    """
    When time zone support is enabled, convert aware datetimes
    to naive datetimes in the current time zone for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        return timezone.make_naive(value)
    return value