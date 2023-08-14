import json

from django.contrib.postgres import forms, lookups
from django.contrib.postgres.fields.array import ArrayField
from django.core import exceptions
from django.db.models import Field, TextField, Transform
from django.db.models.fields.mixins import CheckFieldDefaultMixin
from django.utils.translation import gettext_lazy as _

__all__ = ["HStoreField"]


# [TODO] HStoreField
class HStoreField(CheckFieldDefaultMixin, Field):
    empty_strings_allowed = False
    description = _("Map of strings to strings/nulls")
    default_error_messages = {
        "not_a_string": _("The value of “%(key)s” is not a string or null."),
    }
    _default_hint = ("dict", "{}")

    # [TODO] HStoreField > db_type
    def db_type(self, connection):
        return "hstore"

    # [TODO] HStoreField > get_transform
    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name)

    # [TODO] HStoreField > validate
    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        for key, val in value.items():
            if not isinstance(val, str) and val is not None:
                raise exceptions.ValidationError(
                    self.error_messages["not_a_string"],
                    code="not_a_string",
                    params={"key": key},
                )

    # [TODO] HStoreField > to_python
    def to_python(self, value):
        if isinstance(value, str):
            value = json.loads(value)
        return value

    # [TODO] HStoreField > value_to_string
    def value_to_string(self, obj):
        return json.dumps(self.value_from_object(obj))

    # [TODO] HStoreField > formfield
    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": forms.HStoreField,
                **kwargs,
            }
        )

    # [TODO] HStoreField > get_prep_value
    def get_prep_value(self, value):
        value = super().get_prep_value(value)

        if isinstance(value, dict):
            prep_value = {}
            for key, val in value.items():
                key = str(key)
                if val is not None:
                    val = str(val)
                prep_value[key] = val
            value = prep_value

        if isinstance(value, list):
            value = [str(item) for item in value]

        return value


HStoreField.register_lookup(lookups.DataContains)
HStoreField.register_lookup(lookups.ContainedBy)
HStoreField.register_lookup(lookups.HasKey)
HStoreField.register_lookup(lookups.HasKeys)
HStoreField.register_lookup(lookups.HasAnyKeys)


# [TODO] KeyTransform
class KeyTransform(Transform):
    output_field = TextField()

    # [TODO] KeyTransform > __init__
    def __init__(self, key_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_name = key_name

    # [TODO] KeyTransform > as_sql
    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "(%s -> %%s)" % lhs, tuple(params) + (self.key_name,)


# [TODO] KeyTransformFactory
class KeyTransformFactory:
    # [TODO] KeyTransformFactory > __init__
    def __init__(self, key_name):
        self.key_name = key_name

    # [TODO] KeyTransformFactory > __call__
    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)


# [TODO] KeysTransform
@HStoreField.register_lookup
class KeysTransform(Transform):
    lookup_name = "keys"
    function = "akeys"
    output_field = ArrayField(TextField())


# [TODO] ValuesTransform
@HStoreField.register_lookup
class ValuesTransform(Transform):
    lookup_name = "values"
    function = "avals"
    output_field = ArrayField(TextField())