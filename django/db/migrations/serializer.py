import builtins
import collections.abc
import datetime
import decimal
import enum
import functools
import math
import os
import pathlib
import re
import types
import uuid

from django.conf import SettingsReference
from django.db import models
from django.db.migrations.operations.base import Operation
from django.db.migrations.utils import COMPILED_REGEX_TYPE, RegexObject
from django.utils.functional import LazyObject, Promise
from django.utils.version import PY311, get_docs_version


# [TODO] BaseSerializer
class BaseSerializer:
    # [TODO] BaseSerializer > __init__
    def __init__(self, value):
        self.value = value

    # [TODO] BaseSerializer > serialize
    def serialize(self):
        raise NotImplementedError(
            "Subclasses of BaseSerializer must implement the serialize() method."
        )


# [TODO] BaseSequenceSerializer
class BaseSequenceSerializer(BaseSerializer):
    # [TODO] BaseSequenceSerializer > _format
    def _format(self):
        raise NotImplementedError(
            "Subclasses of BaseSequenceSerializer must implement the _format() method."
        )

    # [TODO] BaseSequenceSerializer > serialize
    def serialize(self):
        imports = set()
        strings = []
        for item in self.value:
            item_string, item_imports = serializer_factory(item).serialize()
            imports.update(item_imports)
            strings.append(item_string)
        value = self._format()
        return value % (", ".join(strings)), imports


# [TODO] BaseUnorderedSequenceSerializer
class BaseUnorderedSequenceSerializer(BaseSequenceSerializer):
    # [TODO] BaseUnorderedSequenceSerializer > __init__
    def __init__(self, value):
        super().__init__(sorted(value, key=repr))


# [TODO] BaseSimpleSerializer
class BaseSimpleSerializer(BaseSerializer):
    # [TODO] BaseSimpleSerializer > serialize
    def serialize(self):
        return repr(self.value), set()


# [TODO] ChoicesSerializer
class ChoicesSerializer(BaseSerializer):
    # [TODO] ChoicesSerializer > serialize
    def serialize(self):
        return serializer_factory(self.value.value).serialize()


# [TODO] DateTimeSerializer
class DateTimeSerializer(BaseSerializer):
    """For datetime.*, except datetime.datetime."""

    # [TODO] DateTimeSerializer > serialize
    def serialize(self):
        return repr(self.value), {"import datetime"}


# [TODO] DatetimeDatetimeSerializer
class DatetimeDatetimeSerializer(BaseSerializer):
    """For datetime.datetime."""

    # [TODO] DatetimeDatetimeSerializer > serialize
    def serialize(self):
        if self.value.tzinfo is not None and self.value.tzinfo != datetime.timezone.utc:
            self.value = self.value.astimezone(datetime.timezone.utc)
        imports = ["import datetime"]
        return repr(self.value), set(imports)


# [TODO] DecimalSerializer
class DecimalSerializer(BaseSerializer):
    # [TODO] DecimalSerializer > serialize
    def serialize(self):
        return repr(self.value), {"from decimal import Decimal"}


# [TODO] DeconstructableSerializer
class DeconstructableSerializer(BaseSerializer):
    # [TODO] DeconstructableSerializer > serialize_deconstructed
    @staticmethod
    def serialize_deconstructed(path, args, kwargs):
        name, imports = DeconstructableSerializer._serialize_path(path)
        strings = []
        for arg in args:
            arg_string, arg_imports = serializer_factory(arg).serialize()
            strings.append(arg_string)
            imports.update(arg_imports)
        for kw, arg in sorted(kwargs.items()):
            arg_string, arg_imports = serializer_factory(arg).serialize()
            imports.update(arg_imports)
            strings.append("%s=%s" % (kw, arg_string))
        return "%s(%s)" % (name, ", ".join(strings)), imports

    # [TODO] DeconstructableSerializer > _serialize_path
    @staticmethod
    def _serialize_path(path):
        module, name = path.rsplit(".", 1)
        if module == "django.db.models":
            imports = {"from django.db import models"}
            name = "models.%s" % name
        else:
            imports = {"import %s" % module}
            name = path
        return name, imports

    # [TODO] DeconstructableSerializer > serialize
    def serialize(self):
        return self.serialize_deconstructed(*self.value.deconstruct())


# [TODO] DictionarySerializer
class DictionarySerializer(BaseSerializer):
    # [TODO] DictionarySerializer > serialize
    def serialize(self):
        imports = set()
        strings = []
        for k, v in sorted(self.value.items()):
            k_string, k_imports = serializer_factory(k).serialize()
            v_string, v_imports = serializer_factory(v).serialize()
            imports.update(k_imports)
            imports.update(v_imports)
            strings.append((k_string, v_string))
        return "{%s}" % (", ".join("%s: %s" % (k, v) for k, v in strings)), imports


# [TODO] EnumSerializer
class EnumSerializer(BaseSerializer):
    # [TODO] EnumSerializer > serialize
    def serialize(self):
        enum_class = self.value.__class__
        module = enum_class.__module__
        if issubclass(enum_class, enum.Flag):
            if PY311:
                members = list(self.value)
            else:
                members, _ = enum._decompose(enum_class, self.value)
                members = reversed(members)
        else:
            members = (self.value,)
        return (
            " | ".join(
                [
                    f"{module}.{enum_class.__qualname__}[{item.name!r}]"
                    for item in members
                ]
            ),
            {"import %s" % module},
        )


# [TODO] FloatSerializer
class FloatSerializer(BaseSimpleSerializer):
    # [TODO] FloatSerializer > serialize
    def serialize(self):
        if math.isnan(self.value) or math.isinf(self.value):
            return 'float("{}")'.format(self.value), set()
        return super().serialize()


# [TODO] FrozensetSerializer
class FrozensetSerializer(BaseUnorderedSequenceSerializer):
    # [TODO] FrozensetSerializer > _format
    def _format(self):
        return "frozenset([%s])"


# [TODO] FunctionTypeSerializer
class FunctionTypeSerializer(BaseSerializer):
    # [TODO] FunctionTypeSerializer > serialize
    def serialize(self):
        if getattr(self.value, "__self__", None) and isinstance(
            self.value.__self__, type
        ):
            klass = self.value.__self__
            module = klass.__module__
            return "%s.%s.%s" % (module, klass.__qualname__, self.value.__name__), {
                "import %s" % module
            }
        # Further error checking
        if self.value.__name__ == "<lambda>":
            raise ValueError("Cannot serialize function: lambda")
        if self.value.__module__ is None:
            raise ValueError("Cannot serialize function %r: No module" % self.value)

        module_name = self.value.__module__

        if "<" not in self.value.__qualname__:  # Qualname can include <locals>
            return "%s.%s" % (module_name, self.value.__qualname__), {
                "import %s" % self.value.__module__
            }

        raise ValueError(
            "Could not find function %s in %s.\n" % (self.value.__name__, module_name)
        )


# [TODO] FunctoolsPartialSerializer
class FunctoolsPartialSerializer(BaseSerializer):
    # [TODO] FunctoolsPartialSerializer > serialize
    def serialize(self):
        # Serialize functools.partial() arguments
        func_string, func_imports = serializer_factory(self.value.func).serialize()
        args_string, args_imports = serializer_factory(self.value.args).serialize()
        keywords_string, keywords_imports = serializer_factory(
            self.value.keywords
        ).serialize()
        # Add any imports needed by arguments
        imports = {"import functools", *func_imports, *args_imports, *keywords_imports}
        return (
            "functools.%s(%s, *%s, **%s)"
            % (
                self.value.__class__.__name__,
                func_string,
                args_string,
                keywords_string,
            ),
            imports,
        )


# [TODO] IterableSerializer
class IterableSerializer(BaseSerializer):
    # [TODO] IterableSerializer > serialize
    def serialize(self):
        imports = set()
        strings = []
        for item in self.value:
            item_string, item_imports = serializer_factory(item).serialize()
            imports.update(item_imports)
            strings.append(item_string)
        # When len(strings)==0, the empty iterable should be serialized as
        # "()", not "(,)" because (,) is invalid Python syntax.
        value = "(%s)" if len(strings) != 1 else "(%s,)"
        return value % (", ".join(strings)), imports


# [TODO] ModelFieldSerializer
class ModelFieldSerializer(DeconstructableSerializer):
    # [TODO] ModelFieldSerializer > serialize
    def serialize(self):
        attr_name, path, args, kwargs = self.value.deconstruct()
        return self.serialize_deconstructed(path, args, kwargs)


# [TODO] ModelManagerSerializer
class ModelManagerSerializer(DeconstructableSerializer):
    # [TODO] ModelManagerSerializer > serialize
    def serialize(self):
        as_manager, manager_path, qs_path, args, kwargs = self.value.deconstruct()
        if as_manager:
            name, imports = self._serialize_path(qs_path)
            return "%s.as_manager()" % name, imports
        else:
            return self.serialize_deconstructed(manager_path, args, kwargs)


# [TODO] OperationSerializer
class OperationSerializer(BaseSerializer):
    # [TODO] OperationSerializer > serialize
    def serialize(self):
        from django.db.migrations.writer import OperationWriter

        string, imports = OperationWriter(self.value, indentation=0).serialize()
        # Nested operation, trailing comma is handled in upper OperationWriter._write()
        return string.rstrip(","), imports


# [TODO] PathLikeSerializer
class PathLikeSerializer(BaseSerializer):
    # [TODO] PathLikeSerializer > serialize
    def serialize(self):
        return repr(os.fspath(self.value)), {}


# [TODO] PathSerializer
class PathSerializer(BaseSerializer):
    # [TODO] PathSerializer > serialize
    def serialize(self):
        # Convert concrete paths to pure paths to avoid issues with migrations
        # generated on one platform being used on a different platform.
        prefix = "Pure" if isinstance(self.value, pathlib.Path) else ""
        return "pathlib.%s%r" % (prefix, self.value), {"import pathlib"}


# [TODO] RegexSerializer
class RegexSerializer(BaseSerializer):
    # [TODO] RegexSerializer > serialize
    def serialize(self):
        regex_pattern, pattern_imports = serializer_factory(
            self.value.pattern
        ).serialize()
        # Turn off default implicit flags (e.g. re.U) because regexes with the
        # same implicit and explicit flags aren't equal.
        flags = self.value.flags ^ re.compile("").flags
        regex_flags, flag_imports = serializer_factory(flags).serialize()
        imports = {"import re", *pattern_imports, *flag_imports}
        args = [regex_pattern]
        if flags:
            args.append(regex_flags)
        return "re.compile(%s)" % ", ".join(args), imports


# [TODO] SequenceSerializer
class SequenceSerializer(BaseSequenceSerializer):
    # [TODO] SequenceSerializer > _format
    def _format(self):
        return "[%s]"


# [TODO] SetSerializer
class SetSerializer(BaseUnorderedSequenceSerializer):
    # [TODO] SetSerializer > _format
    def _format(self):
        # Serialize as a set literal except when value is empty because {}
        # is an empty dict.
        return "{%s}" if self.value else "set(%s)"


# [TODO] SettingsReferenceSerializer
class SettingsReferenceSerializer(BaseSerializer):
    # [TODO] SettingsReferenceSerializer > serialize
    def serialize(self):
        return "settings.%s" % self.value.setting_name, {
            "from django.conf import settings"
        }


# [TODO] TupleSerializer
class TupleSerializer(BaseSequenceSerializer):
    # [TODO] TupleSerializer > _format
    def _format(self):
        # When len(value)==0, the empty tuple should be serialized as "()",
        # not "(,)" because (,) is invalid Python syntax.
        return "(%s)" if len(self.value) != 1 else "(%s,)"


# [TODO] TypeSerializer
class TypeSerializer(BaseSerializer):
    # [TODO] TypeSerializer > serialize
    def serialize(self):
        special_cases = [
            (models.Model, "models.Model", ["from django.db import models"]),
            (types.NoneType, "types.NoneType", ["import types"]),
        ]
        for case, string, imports in special_cases:
            if case is self.value:
                return string, set(imports)
        if hasattr(self.value, "__module__"):
            module = self.value.__module__
            if module == builtins.__name__:
                return self.value.__name__, set()
            else:
                return "%s.%s" % (module, self.value.__qualname__), {
                    "import %s" % module
                }


# [TODO] UUIDSerializer
class UUIDSerializer(BaseSerializer):
    # [TODO] UUIDSerializer > serialize
    def serialize(self):
        return "uuid.%s" % repr(self.value), {"import uuid"}


# [TODO] Serializer
class Serializer:
    _registry = {
        # Some of these are order-dependent.
        frozenset: FrozensetSerializer,
        list: SequenceSerializer,
        set: SetSerializer,
        tuple: TupleSerializer,
        dict: DictionarySerializer,
        models.Choices: ChoicesSerializer,
        enum.Enum: EnumSerializer,
        datetime.datetime: DatetimeDatetimeSerializer,
        (datetime.date, datetime.timedelta, datetime.time): DateTimeSerializer,
        SettingsReference: SettingsReferenceSerializer,
        float: FloatSerializer,
        (bool, int, types.NoneType, bytes, str, range): BaseSimpleSerializer,
        decimal.Decimal: DecimalSerializer,
        (functools.partial, functools.partialmethod): FunctoolsPartialSerializer,
        (
            types.FunctionType,
            types.BuiltinFunctionType,
            types.MethodType,
        ): FunctionTypeSerializer,
        collections.abc.Iterable: IterableSerializer,
        (COMPILED_REGEX_TYPE, RegexObject): RegexSerializer,
        uuid.UUID: UUIDSerializer,
        pathlib.PurePath: PathSerializer,
        os.PathLike: PathLikeSerializer,
    }

    # [TODO] Serializer > register
    @classmethod
    def register(cls, type_, serializer):
        if not issubclass(serializer, BaseSerializer):
            raise ValueError(
                "'%s' must inherit from 'BaseSerializer'." % serializer.__name__
            )
        cls._registry[type_] = serializer

    # [TODO] Serializer > unregister
    @classmethod
    def unregister(cls, type_):
        cls._registry.pop(type_)


# [TODO] serializer_factory
def serializer_factory(value):
    if isinstance(value, Promise):
        value = str(value)
    elif isinstance(value, LazyObject):
        # The unwrapped value is returned as the first item of the arguments
        # tuple.
        value = value.__reduce__()[1][0]

    if isinstance(value, models.Field):
        return ModelFieldSerializer(value)
    if isinstance(value, models.manager.BaseManager):
        return ModelManagerSerializer(value)
    if isinstance(value, Operation):
        return OperationSerializer(value)
    if isinstance(value, type):
        return TypeSerializer(value)
    # Anything that knows how to deconstruct itself.
    if hasattr(value, "deconstruct"):
        return DeconstructableSerializer(value)
    for type_, serializer_cls in Serializer._registry.items():
        if isinstance(value, type_):
            return serializer_cls(value)
    raise ValueError(
        "Cannot serialize: %r\nThere are some values Django cannot serialize into "
        "migration files.\nFor more, see https://docs.djangoproject.com/en/%s/"
        "topics/migrations/#migration-serializing" % (value, get_docs_version())
    )