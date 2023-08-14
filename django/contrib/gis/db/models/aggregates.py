from django.contrib.gis.db.models.fields import (
    ExtentField,
    GeometryCollectionField,
    GeometryField,
    LineStringField,
)
from django.db.models import Aggregate, Func, Value
from django.utils.functional import cached_property

__all__ = ["Collect", "Extent", "Extent3D", "MakeLine", "Union"]


# [TODO] GeoAggregate
class GeoAggregate(Aggregate):
    function = None
    is_extent = False

    # [TODO] GeoAggregate > output_field
    @cached_property
    def output_field(self):
        return self.output_field_class(self.source_expressions[0].output_field.srid)

    # [TODO] GeoAggregate > as_sql
    def as_sql(self, compiler, connection, function=None, **extra_context):
        # this will be called again in parent, but it's needed now - before
        # we get the spatial_aggregate_name
        connection.ops.check_expression_support(self)
        return super().as_sql(
            compiler,
            connection,
            function=function or connection.ops.spatial_aggregate_name(self.name),
            **extra_context,
        )

    # [TODO] GeoAggregate > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        if not self.is_extent:
            tolerance = self.extra.get("tolerance") or getattr(self, "tolerance", 0.05)
            clone = self.copy()
            source_expressions = self.get_source_expressions()
            if self.filter:
                source_expressions.pop()
            spatial_type_expr = Func(
                *source_expressions,
                Value(tolerance),
                function="SDOAGGRTYPE",
                output_field=self.output_field,
            )
            source_expressions = [spatial_type_expr]
            if self.filter:
                source_expressions.append(self.filter)
            clone.set_source_expressions(source_expressions)
            return clone.as_sql(compiler, connection, **extra_context)
        return self.as_sql(compiler, connection, **extra_context)

    # [TODO] GeoAggregate > resolve_expression
    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        for field in c.get_source_fields():
            if not hasattr(field, "geom_type"):
                raise ValueError(
                    "Geospatial aggregates only allowed on geometry fields."
                )
        return c


# [TODO] Collect
class Collect(GeoAggregate):
    name = "Collect"
    output_field_class = GeometryCollectionField


# [TODO] Extent
class Extent(GeoAggregate):
    name = "Extent"
    is_extent = "2D"

    # [TODO] Extent > __init__
    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    # [TODO] Extent > convert_value
    def convert_value(self, value, expression, connection):
        return connection.ops.convert_extent(value)


# [TODO] Extent3D
class Extent3D(GeoAggregate):
    name = "Extent3D"
    is_extent = "3D"

    # [TODO] Extent3D > __init__
    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    # [TODO] Extent3D > convert_value
    def convert_value(self, value, expression, connection):
        return connection.ops.convert_extent3d(value)


# [TODO] MakeLine
class MakeLine(GeoAggregate):
    name = "MakeLine"
    output_field_class = LineStringField


# [TODO] Union
class Union(GeoAggregate):
    name = "Union"
    output_field_class = GeometryField