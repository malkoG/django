from django.core import checks

NOT_PROVIDED = object()


# [TODO] FieldCacheMixin
class FieldCacheMixin:
    """Provide an API for working with the model's fields value cache."""

    # [TODO] FieldCacheMixin > get_cache_name
    def get_cache_name(self):
        raise NotImplementedError

    # [TODO] FieldCacheMixin > get_cached_value
    def get_cached_value(self, instance, default=NOT_PROVIDED):
        cache_name = self.get_cache_name()
        try:
            return instance._state.fields_cache[cache_name]
        except KeyError:
            if default is NOT_PROVIDED:
                raise
            return default

    # [TODO] FieldCacheMixin > is_cached
    def is_cached(self, instance):
        return self.get_cache_name() in instance._state.fields_cache

    # [TODO] FieldCacheMixin > set_cached_value
    def set_cached_value(self, instance, value):
        instance._state.fields_cache[self.get_cache_name()] = value

    # [TODO] FieldCacheMixin > delete_cached_value
    def delete_cached_value(self, instance):
        del instance._state.fields_cache[self.get_cache_name()]


# [TODO] CheckFieldDefaultMixin
class CheckFieldDefaultMixin:
    _default_hint = ("<valid default>", "<invalid default>")

    # [TODO] CheckFieldDefaultMixin > _check_default
    def _check_default(self):
        if (
            self.has_default()
            and self.default is not None
            and not callable(self.default)
        ):
            return [
                checks.Warning(
                    "%s default should be a callable instead of an instance "
                    "so that it's not shared between all field instances."
                    % (self.__class__.__name__,),
                    hint=(
                        "Use a callable instead, e.g., use `%s` instead of "
                        "`%s`." % self._default_hint
                    ),
                    obj=self,
                    id="fields.E010",
                )
            ]
        else:
            return []

    # [TODO] CheckFieldDefaultMixin > check
    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_default())
        return errors