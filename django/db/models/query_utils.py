"""
Various data structures used in query construction.

Factored out from django.db.models.query to avoid making the main module very
large and/or so that they can be used by other modules without getting into
circular import difficulties.
"""
import functools
import inspect
import logging
from collections import namedtuple

from django.core.exceptions import FieldError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.db.models.constants import LOOKUP_SEP
from django.utils import tree

logger = logging.getLogger("django.db.models")

# PathInfo is used when converting lookups (fk__somecol). The contents
# describe the relation in Model terms (model Options and Fields for both
# sides of the relation. The join_field is the field backing the relation.
PathInfo = namedtuple(
    "PathInfo",
    "from_opts to_opts target_fields join_field m2m direct filtered_relation",
)


# [TODO] subclasses
def subclasses(cls):
    yield cls
    for subclass in cls.__subclasses__():
        yield from subclasses(subclass)


# [TODO] Q
class Q(tree.Node):
    """
    Encapsulate filters as objects that can then be combined logically (using
    `&` and `|`).
    """

    # Connection types
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    default = AND
    conditional = True

    # [TODO] Q > __init__
    def __init__(self, *args, _connector=None, _negated=False, **kwargs):
        super().__init__(
            children=[*args, *sorted(kwargs.items())],
            connector=_connector,
            negated=_negated,
        )

    # [TODO] Q > _combine
    def _combine(self, other, conn):
        if getattr(other, "conditional", False) is False:
            raise TypeError(other)
        if not self:
            return other.copy()
        if not other and isinstance(other, Q):
            return self.copy()

        obj = self.create(connector=conn)
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    # [TODO] Q > __or__
    def __or__(self, other):
        return self._combine(other, self.OR)

    # [TODO] Q > __and__
    def __and__(self, other):
        return self._combine(other, self.AND)

    # [TODO] Q > __xor__
    def __xor__(self, other):
        return self._combine(other, self.XOR)

    # [TODO] Q > __invert__
    def __invert__(self):
        obj = self.copy()
        obj.negate()
        return obj

    # [TODO] Q > resolve_expression
    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        # We must promote any new joins to left outer joins so that when Q is
        # used as an expression, rows aren't filtered due to joins.
        clause, joins = query._add_q(
            self,
            reuse,
            allow_joins=allow_joins,
            split_subq=False,
            check_filterable=False,
            summarize=summarize,
        )
        query.promote_joins(joins)
        return clause

    # [TODO] Q > flatten
    def flatten(self):
        """
        Recursively yield this Q object and all subexpressions, in depth-first
        order.
        """
        yield self
        for child in self.children:
            if isinstance(child, tuple):
                # Use the lookup.
                child = child[1]
            if hasattr(child, "flatten"):
                yield from child.flatten()
            else:
                yield child

    # [TODO] Q > check
    def check(self, against, using=DEFAULT_DB_ALIAS):
        """
        Do a database query to check if the expressions of the Q instance
        matches against the expressions.
        """
        # Avoid circular imports.
        from django.db.models import BooleanField, Value
        from django.db.models.functions import Coalesce
        from django.db.models.sql import Query
        from django.db.models.sql.constants import SINGLE

        query = Query(None)
        for name, value in against.items():
            if not hasattr(value, "resolve_expression"):
                value = Value(value)
            query.add_annotation(value, name, select=False)
        query.add_annotation(Value(1), "_check")
        # This will raise a FieldError if a field is missing in "against".
        if connections[using].features.supports_comparing_boolean_expr:
            query.add_q(Q(Coalesce(self, True, output_field=BooleanField())))
        else:
            query.add_q(self)
        compiler = query.get_compiler(using=using)
        try:
            return compiler.execute_sql(SINGLE) is not None
        except DatabaseError as e:
            logger.warning("Got a database error calling check() on %r: %s", self, e)
            return True

    # [TODO] Q > deconstruct
    def deconstruct(self):
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        if path.startswith("django.db.models.query_utils"):
            path = path.replace("django.db.models.query_utils", "django.db.models")
        args = tuple(self.children)
        kwargs = {}
        if self.connector != self.default:
            kwargs["_connector"] = self.connector
        if self.negated:
            kwargs["_negated"] = True
        return path, args, kwargs


# [TODO] DeferredAttribute
class DeferredAttribute:
    """
    A wrapper for a deferred-loading field. When the value is read from this
    object the first time, the query is executed.
    """

    # [TODO] DeferredAttribute > __init__
    def __init__(self, field):
        self.field = field

    # [TODO] DeferredAttribute > __get__
    def __get__(self, instance, cls=None):
        """
        Retrieve and caches the value from the datastore on the first lookup.
        Return the cached value.
        """
        if instance is None:
            return self
        data = instance.__dict__
        field_name = self.field.attname
        if field_name not in data:
            # Let's see if the field is part of the parent chain. If so we
            # might be able to reuse the already loaded value. Refs #18343.
            val = self._check_parent_chain(instance)
            if val is None:
                instance.refresh_from_db(fields=[field_name])
            else:
                data[field_name] = val
        return data[field_name]

    # [TODO] DeferredAttribute > _check_parent_chain
    def _check_parent_chain(self, instance):
        """
        Check if the field value can be fetched from a parent field already
        loaded in the instance. This can be done if the to-be fetched
        field is a primary key field.
        """
        opts = instance._meta
        link_field = opts.get_ancestor_link(self.field.model)
        if self.field.primary_key and self.field != link_field:
            return getattr(instance, link_field.attname)
        return None


# [TODO] class_or_instance_method
class class_or_instance_method:
    """
    Hook used in RegisterLookupMixin to return partial functions depending on
    the caller type (instance or class of models.Field).
    """

    # [TODO] class_or_instance_method > __init__
    def __init__(self, class_method, instance_method):
        self.class_method = class_method
        self.instance_method = instance_method

    # [TODO] class_or_instance_method > __get__
    def __get__(self, instance, owner):
        if instance is None:
            return functools.partial(self.class_method, owner)
        return functools.partial(self.instance_method, instance)


# [TODO] RegisterLookupMixin
class RegisterLookupMixin:
    # [TODO] RegisterLookupMixin > _get_lookup
    def _get_lookup(self, lookup_name):
        return self.get_lookups().get(lookup_name, None)

    # [TODO] RegisterLookupMixin > get_class_lookups
    @functools.cache
    def get_class_lookups(cls):
        class_lookups = [
            parent.__dict__.get("class_lookups", {}) for parent in inspect.getmro(cls)
        ]
        return cls.merge_dicts(class_lookups)

    # [TODO] RegisterLookupMixin > get_instance_lookups
    def get_instance_lookups(self):
        class_lookups = self.get_class_lookups()
        if instance_lookups := getattr(self, "instance_lookups", None):
            return {**class_lookups, **instance_lookups}
        return class_lookups

    get_lookups = class_or_instance_method(get_class_lookups, get_instance_lookups)
    get_class_lookups = classmethod(get_class_lookups)

    # [TODO] RegisterLookupMixin > get_lookup
    def get_lookup(self, lookup_name):
        from django.db.models.lookups import Lookup

        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, "output_field"):
            return self.output_field.get_lookup(lookup_name)
        if found is not None and not issubclass(found, Lookup):
            return None
        return found

    # [TODO] RegisterLookupMixin > get_transform
    def get_transform(self, lookup_name):
        from django.db.models.lookups import Transform

        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, "output_field"):
            return self.output_field.get_transform(lookup_name)
        if found is not None and not issubclass(found, Transform):
            return None
        return found

    # [TODO] RegisterLookupMixin > merge_dicts
    @staticmethod
    def merge_dicts(dicts):
        """
        Merge dicts in reverse to preference the order of the original list. e.g.,
        merge_dicts([a, b]) will preference the keys in 'a' over those in 'b'.
        """
        merged = {}
        for d in reversed(dicts):
            merged.update(d)
        return merged

    # [TODO] RegisterLookupMixin > _clear_cached_class_lookups
    @classmethod
    def _clear_cached_class_lookups(cls):
        for subclass in subclasses(cls):
            subclass.get_class_lookups.cache_clear()

    # [TODO] RegisterLookupMixin > register_class_lookup
    def register_class_lookup(cls, lookup, lookup_name=None):
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        if "class_lookups" not in cls.__dict__:
            cls.class_lookups = {}
        cls.class_lookups[lookup_name] = lookup
        cls._clear_cached_class_lookups()
        return lookup

    # [TODO] RegisterLookupMixin > register_instance_lookup
    def register_instance_lookup(self, lookup, lookup_name=None):
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        if "instance_lookups" not in self.__dict__:
            self.instance_lookups = {}
        self.instance_lookups[lookup_name] = lookup
        return lookup

    register_lookup = class_or_instance_method(
        register_class_lookup, register_instance_lookup
    )
    register_class_lookup = classmethod(register_class_lookup)

    # [TODO] RegisterLookupMixin > _unregister_class_lookup
    def _unregister_class_lookup(cls, lookup, lookup_name=None):
        """
        Remove given lookup from cls lookups. For use in tests only as it's
        not thread-safe.
        """
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        del cls.class_lookups[lookup_name]
        cls._clear_cached_class_lookups()

    # [TODO] RegisterLookupMixin > _unregister_instance_lookup
    def _unregister_instance_lookup(self, lookup, lookup_name=None):
        """
        Remove given lookup from instance lookups. For use in tests only as
        it's not thread-safe.
        """
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        del self.instance_lookups[lookup_name]

    _unregister_lookup = class_or_instance_method(
        _unregister_class_lookup, _unregister_instance_lookup
    )
    _unregister_class_lookup = classmethod(_unregister_class_lookup)


# [TODO] select_related_descend
def select_related_descend(field, restricted, requested, select_mask, reverse=False):
    """
    Return True if this field should be used to descend deeper for
    select_related() purposes. Used by both the query construction code
    (compiler.get_related_selections()) and the model instance creation code
    (compiler.klass_info).

    Arguments:
     * field - the field to be checked
     * restricted - a boolean field, indicating if the field list has been
       manually restricted using a requested clause)
     * requested - The select_related() dictionary.
     * select_mask - the dictionary of selected fields.
     * reverse - boolean, True if we are checking a reverse select related
    """
    if not field.remote_field:
        return False
    if field.remote_field.parent_link and not reverse:
        return False
    if restricted:
        if reverse and field.related_query_name() not in requested:
            return False
        if not reverse and field.name not in requested:
            return False
    if not restricted and field.null:
        return False
    if (
        restricted
        and select_mask
        and field.name in requested
        and field not in select_mask
    ):
        raise FieldError(
            f"Field {field.model._meta.object_name}.{field.name} cannot be both "
            "deferred and traversed using select_related at the same time."
        )
    return True


# [TODO] refs_expression
def refs_expression(lookup_parts, annotations):
    """
    Check if the lookup_parts contains references to the given annotations set.
    Because the LOOKUP_SEP is contained in the default annotation names, check
    each prefix of the lookup_parts for a match.
    """
    for n in range(1, len(lookup_parts) + 1):
        level_n_lookup = LOOKUP_SEP.join(lookup_parts[0:n])
        if annotations.get(level_n_lookup):
            return level_n_lookup, lookup_parts[n:]
    return None, ()


# [TODO] check_rel_lookup_compatibility
def check_rel_lookup_compatibility(model, target_opts, field):
    """
    Check that self.model is compatible with target_opts. Compatibility
    is OK if:
      1) model and opts match (where proxy inheritance is removed)
      2) model is parent of opts' model or the other way around
    """

    def check(opts):
        return (
            model._meta.concrete_model == opts.concrete_model
            or opts.concrete_model in model._meta.get_parent_list()
            or model in opts.get_parent_list()
        )

    # If the field is a primary key, then doing a query against the field's
    # model is ok, too. Consider the case:
    # class Restaurant(models.Model):
    #     place = OneToOneField(Place, primary_key=True):
    # Restaurant.objects.filter(pk__in=Restaurant.objects.all()).
    # If we didn't have the primary key check, then pk__in (== place__in) would
    # give Place's opts as the target opts, but Restaurant isn't compatible
    # with that. This logic applies only to primary keys, as when doing __in=qs,
    # we are going to turn this into __in=qs.values('pk') later on.
    return check(target_opts) or (
        getattr(field, "primary_key", False) and check(field.model._meta)
    )


# [TODO] FilteredRelation
class FilteredRelation:
    """Specify custom filtering in the ON clause of SQL joins."""

    # [TODO] FilteredRelation > __init__
    def __init__(self, relation_name, *, condition=Q()):
        if not relation_name:
            raise ValueError("relation_name cannot be empty.")
        self.relation_name = relation_name
        self.alias = None
        if not isinstance(condition, Q):
            raise ValueError("condition argument must be a Q() instance.")
        # .condition and .resolved_condition have to be stored independently
        # as the former must remain unchanged for Join.__eq__ to remain stable
        # and reusable even once their .filtered_relation are resolved.
        self.condition = condition
        self.resolved_condition = None

    # [TODO] FilteredRelation > __eq__
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.relation_name == other.relation_name
            and self.alias == other.alias
            and self.condition == other.condition
        )

    # [TODO] FilteredRelation > clone
    def clone(self):
        clone = FilteredRelation(self.relation_name, condition=self.condition)
        clone.alias = self.alias
        if (resolved_condition := self.resolved_condition) is not None:
            clone.resolved_condition = resolved_condition.clone()
        return clone

    # [TODO] FilteredRelation > relabeled_clone
    def relabeled_clone(self, change_map):
        clone = self.clone()
        if resolved_condition := clone.resolved_condition:
            clone.resolved_condition = resolved_condition.relabeled_clone(change_map)
        return clone

    # [TODO] FilteredRelation > resolve_expression
    def resolve_expression(self, query, reuse, *args, **kwargs):
        clone = self.clone()
        clone.resolved_condition = query.build_filter(
            self.condition,
            can_reuse=reuse,
            allow_joins=True,
            split_subq=False,
            update_join_types=False,
        )[0]
        return clone

    # [TODO] FilteredRelation > as_sql
    def as_sql(self, compiler, connection):
        return compiler.compile(self.resolved_condition)