import functools
import uuid


# [TODO] IntConverter
class IntConverter:
    regex = "[0-9]+"

    # [TODO] IntConverter > to_python
    def to_python(self, value):
        return int(value)

    # [TODO] IntConverter > to_url
    def to_url(self, value):
        return str(value)


# [TODO] StringConverter
class StringConverter:
    regex = "[^/]+"

    # [TODO] StringConverter > to_python
    def to_python(self, value):
        return value

    # [TODO] StringConverter > to_url
    def to_url(self, value):
        return value


# [TODO] UUIDConverter
class UUIDConverter:
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    # [TODO] UUIDConverter > to_python
    def to_python(self, value):
        return uuid.UUID(value)

    # [TODO] UUIDConverter > to_url
    def to_url(self, value):
        return str(value)


# [TODO] SlugConverter
class SlugConverter(StringConverter):
    regex = "[-a-zA-Z0-9_]+"


# [TODO] PathConverter
class PathConverter(StringConverter):
    regex = ".+"


DEFAULT_CONVERTERS = {
    "int": IntConverter(),
    "path": PathConverter(),
    "slug": SlugConverter(),
    "str": StringConverter(),
    "uuid": UUIDConverter(),
}


REGISTERED_CONVERTERS = {}


# [TODO] register_converter
def register_converter(converter, type_name):
    REGISTERED_CONVERTERS[type_name] = converter()
    get_converters.cache_clear()


# [TODO] get_converters
@functools.cache
def get_converters():
    return {**DEFAULT_CONVERTERS, **REGISTERED_CONVERTERS}


# [TODO] get_converter
def get_converter(raw_converter):
    return get_converters()[raw_converter]