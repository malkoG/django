from decimal import Decimal

from django.contrib.gis.db.models.fields import BaseSpatialField, GeometryField
from django.contrib.gis.db.models.sql import AreaField, DistanceField
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import FieldError
from django.db import NotSupportedError
from django.db.models import (
    BinaryField,
    BooleanField,
    FloatField,
    Func,
    IntegerField,
    TextField,
    Transform,
    Value,
)
from django.db.models.functions import Cast
from django.utils.functional import cached_property

NUMERIC_TYPES = (int, float, Decimal)


# [TODO] GeoFuncMixin
class GeoFuncMixin:
    function = None
    geom_param_pos = (0,)

    # [TODO] GeoFuncMixin > __init__
    def __init__(self, *expressions, **extra):
        super().__init__(*expressions, **extra)

        # Ensure that value expressions are geometric.
        for pos in self.geom_param_pos:
            expr = self.source_expressions[pos]
            if not isinstance(expr, Value):
                continue
            try:
                output_field = expr.output_field
            except FieldError:
                output_field = None
            geom = expr.value
            if (
                not isinstance(geom, GEOSGeometry)
                or output_field
                and not isinstance(output_field, GeometryField)
            ):
                raise TypeError(
                    "%s function requires a geometric argument in position %d."
                    % (self.name, pos + 1)
                )
            if not geom.srid and not output_field:
                raise ValueError("SRID is required for all geometries.")
            if not output_field:
                self.source_expressions[pos] = Value(
                    geom, output_field=GeometryField(srid=geom.srid)
                )

    # [TODO] GeoFuncMixin > name
    @property
    def name(self):
        return self.__class__.__name__

    # [TODO] GeoFuncMixin > geo_field
    @cached_property
    def geo_field(self):
        return self.source_expressions[self.geom_param_pos[0]].field

    # [TODO] GeoFuncMixin > as_sql
    def as_sql(self, compiler, connection, function=None, **extra_context):
        if self.function is None and function is None:
            function = connection.ops.spatial_function_name(self.name)
        return super().as_sql(compiler, connection, function=function, **extra_context)

    # [TODO] GeoFuncMixin > resolve_expression
    def resolve_expression(self, *args, **kwargs):
        res = super().resolve_expression(*args, **kwargs)
        if not self.geom_param_pos:
            return res

        # Ensure that expressions are geometric.
        source_fields = res.get_source_fields()
        for pos in self.geom_param_pos:
            field = source_fields[pos]
            if not isinstance(field, GeometryField):
                raise TypeError(
                    "%s function requires a GeometryField in position %s, got %s."
                    % (
                        self.name,
                        pos + 1,
                        type(field).__name__,
                    )
                )

        base_srid = res.geo_field.srid
        for pos in self.geom_param_pos[1:]:
            expr = res.source_expressions[pos]
            expr_srid = expr.output_field.srid
            if expr_srid != base_srid:
                # Automatic SRID conversion so objects are comparable.
                res.source_expressions[pos] = Transform(
                    expr, base_srid
                ).resolve_expression(*args, **kwargs)
        return res

    # [TODO] GeoFuncMixin > _handle_param
    def _handle_param(self, value, param_name="", check_types=None):
        if not hasattr(value, "resolve_expression"):
            if check_types and not isinstance(value, check_types):
                raise TypeError(
                    "The %s parameter has the wrong type: should be %s."
                    % (param_name, check_types)
                )
        return value


# [TODO] GeoFunc
class GeoFunc(GeoFuncMixin, Func):
    pass


# [TODO] GeomOutputGeoFunc
class GeomOutputGeoFunc(GeoFunc):
    # [TODO] GeomOutputGeoFunc > output_field
    @cached_property
    def output_field(self):
        return GeometryField(srid=self.geo_field.srid)


# [TODO] SQLiteDecimalToFloatMixin
class SQLiteDecimalToFloatMixin:
    """
    By default, Decimal values are converted to str by the SQLite backend, which
    is not acceptable by the GIS functions expecting numeric values.
    """

    # [TODO] SQLiteDecimalToFloatMixin > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        copy = self.copy()
        copy.set_source_expressions(
            [
                Value(float(expr.value))
                if hasattr(expr, "value") and isinstance(expr.value, Decimal)
                else expr
                for expr in copy.get_source_expressions()
            ]
        )
        return copy.as_sql(compiler, connection, **extra_context)


# [TODO] OracleToleranceMixin
class OracleToleranceMixin:
    tolerance = 0.05

    # [TODO] OracleToleranceMixin > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        tolerance = Value(
            self._handle_param(
                self.extra.get("tolerance", self.tolerance),
                "tolerance",
                NUMERIC_TYPES,
            )
        )
        clone = self.copy()
        clone.set_source_expressions([*self.get_source_expressions(), tolerance])
        return clone.as_sql(compiler, connection, **extra_context)


# [TODO] Area
class Area(OracleToleranceMixin, GeoFunc):
    arity = 1

    # [TODO] Area > output_field
    @cached_property
    def output_field(self):
        return AreaField(self.geo_field)

    # [TODO] Area > as_sql
    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_area_geodetic and self.geo_field.geodetic(
            connection
        ):
            raise NotSupportedError(
                "Area on geodetic coordinate systems not supported."
            )
        return super().as_sql(compiler, connection, **extra_context)

    # [TODO] Area > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        if self.geo_field.geodetic(connection):
            extra_context["template"] = "%(function)s(%(expressions)s, %(spheroid)d)"
            extra_context["spheroid"] = True
        return self.as_sql(compiler, connection, **extra_context)


# [TODO] Azimuth
class Azimuth(GeoFunc):
    output_field = FloatField()
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] AsGeoJSON
class AsGeoJSON(GeoFunc):
    output_field = TextField()

    # [TODO] AsGeoJSON > __init__
    def __init__(self, expression, bbox=False, crs=False, precision=8, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, "precision", int))
        options = 0
        if crs and bbox:
            options = 3
        elif bbox:
            options = 1
        elif crs:
            options = 2
        if options:
            expressions.append(options)
        super().__init__(*expressions, **extra)

    # [TODO] AsGeoJSON > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        source_expressions = self.get_source_expressions()
        clone = self.copy()
        clone.set_source_expressions(source_expressions[:1])
        return super(AsGeoJSON, clone).as_sql(compiler, connection, **extra_context)


# [TODO] AsGML
class AsGML(GeoFunc):
    geom_param_pos = (1,)
    output_field = TextField()

    # [TODO] AsGML > __init__
    def __init__(self, expression, version=2, precision=8, **extra):
        expressions = [version, expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, "precision", int))
        super().__init__(*expressions, **extra)

    # [TODO] AsGML > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        source_expressions = self.get_source_expressions()
        version = source_expressions[0]
        clone = self.copy()
        clone.set_source_expressions([source_expressions[1]])
        extra_context["function"] = (
            "SDO_UTIL.TO_GML311GEOMETRY"
            if version.value == 3
            else "SDO_UTIL.TO_GMLGEOMETRY"
        )
        return super(AsGML, clone).as_sql(compiler, connection, **extra_context)


# [TODO] AsKML
class AsKML(GeoFunc):
    output_field = TextField()

    # [TODO] AsKML > __init__
    def __init__(self, expression, precision=8, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, "precision", int))
        super().__init__(*expressions, **extra)


# [TODO] AsSVG
class AsSVG(GeoFunc):
    output_field = TextField()

    # [TODO] AsSVG > __init__
    def __init__(self, expression, relative=False, precision=8, **extra):
        relative = (
            relative if hasattr(relative, "resolve_expression") else int(relative)
        )
        expressions = [
            expression,
            relative,
            self._handle_param(precision, "precision", int),
        ]
        super().__init__(*expressions, **extra)


# [TODO] AsWKB
class AsWKB(GeoFunc):
    output_field = BinaryField()
    arity = 1


# [TODO] AsWKT
class AsWKT(GeoFunc):
    output_field = TextField()
    arity = 1


# [TODO] BoundingCircle
class BoundingCircle(OracleToleranceMixin, GeomOutputGeoFunc):
    # [TODO] BoundingCircle > __init__
    def __init__(self, expression, num_seg=48, **extra):
        super().__init__(expression, num_seg, **extra)

    # [TODO] BoundingCircle > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        clone = self.copy()
        clone.set_source_expressions([self.get_source_expressions()[0]])
        return super(BoundingCircle, clone).as_oracle(
            compiler, connection, **extra_context
        )


# [TODO] Centroid
class Centroid(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 1


# [TODO] ClosestPoint
class ClosestPoint(GeomOutputGeoFunc):
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] Difference
class Difference(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] DistanceResultMixin
class DistanceResultMixin:
    # [TODO] DistanceResultMixin > output_field
    @cached_property
    def output_field(self):
        return DistanceField(self.geo_field)

    # [TODO] DistanceResultMixin > source_is_geography
    def source_is_geography(self):
        return self.geo_field.geography and self.geo_field.srid == 4326


# [TODO] Distance
class Distance(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    geom_param_pos = (0, 1)
    spheroid = None

    # [TODO] Distance > __init__
    def __init__(self, expr1, expr2, spheroid=None, **extra):
        expressions = [expr1, expr2]
        if spheroid is not None:
            self.spheroid = self._handle_param(spheroid, "spheroid", bool)
        super().__init__(*expressions, **extra)

    # [TODO] Distance > as_postgresql
    def as_postgresql(self, compiler, connection, **extra_context):
        clone = self.copy()
        function = None
        expr2 = clone.source_expressions[1]
        geography = self.source_is_geography()
        if expr2.output_field.geography != geography:
            if isinstance(expr2, Value):
                expr2.output_field.geography = geography
            else:
                clone.source_expressions[1] = Cast(
                    expr2,
                    GeometryField(srid=expr2.output_field.srid, geography=geography),
                )

        if not geography and self.geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need special
            # distance functions.
            if self.spheroid:
                # DistanceSpheroid is more accurate and resource intensive than
                # DistanceSphere.
                function = connection.ops.spatial_function_name("DistanceSpheroid")
                # Replace boolean param by the real spheroid of the base field
                clone.source_expressions.append(
                    Value(self.geo_field.spheroid(connection))
                )
            else:
                function = connection.ops.spatial_function_name("DistanceSphere")
        return super(Distance, clone).as_sql(
            compiler, connection, function=function, **extra_context
        )

    # [TODO] Distance > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        if self.geo_field.geodetic(connection):
            # SpatiaLite returns NULL instead of zero on geodetic coordinates
            extra_context[
                "template"
            ] = "COALESCE(%(function)s(%(expressions)s, %(spheroid)s), 0)"
            extra_context["spheroid"] = int(bool(self.spheroid))
        return super().as_sql(compiler, connection, **extra_context)


# [TODO] Envelope
class Envelope(GeomOutputGeoFunc):
    arity = 1


# [TODO] ForcePolygonCW
class ForcePolygonCW(GeomOutputGeoFunc):
    arity = 1


# [TODO] FromWKB
class FromWKB(GeoFunc):
    output_field = GeometryField(srid=0)
    arity = 1
    geom_param_pos = ()


# [TODO] FromWKT
class FromWKT(GeoFunc):
    output_field = GeometryField(srid=0)
    arity = 1
    geom_param_pos = ()


# [TODO] GeoHash
class GeoHash(GeoFunc):
    output_field = TextField()

    # [TODO] GeoHash > __init__
    def __init__(self, expression, precision=None, **extra):
        expressions = [expression]
        if precision is not None:
            expressions.append(self._handle_param(precision, "precision", int))
        super().__init__(*expressions, **extra)

    # [TODO] GeoHash > as_mysql
    def as_mysql(self, compiler, connection, **extra_context):
        clone = self.copy()
        # If no precision is provided, set it to the maximum.
        if len(clone.source_expressions) < 2:
            clone.source_expressions.append(Value(100))
        return clone.as_sql(compiler, connection, **extra_context)


# [TODO] GeometryDistance
class GeometryDistance(GeoFunc):
    output_field = FloatField()
    arity = 2
    function = ""
    arg_joiner = " <-> "
    geom_param_pos = (0, 1)


# [TODO] Intersection
class Intersection(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] IsEmpty
@BaseSpatialField.register_lookup
class IsEmpty(GeoFuncMixin, Transform):
    lookup_name = "isempty"
    output_field = BooleanField()


# [TODO] IsValid
@BaseSpatialField.register_lookup
class IsValid(OracleToleranceMixin, GeoFuncMixin, Transform):
    lookup_name = "isvalid"
    output_field = BooleanField()

    def as_oracle(self, compiler, connection, **extra_context):
        sql, params = super().as_oracle(compiler, connection, **extra_context)
        return "CASE %s WHEN 'TRUE' THEN 1 ELSE 0 END" % sql, params


# [TODO] Length
class Length(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    # [TODO] Length > __init__
    def __init__(self, expr1, spheroid=True, **extra):
        self.spheroid = spheroid
        super().__init__(expr1, **extra)

    # [TODO] Length > as_sql
    def as_sql(self, compiler, connection, **extra_context):
        if (
            self.geo_field.geodetic(connection)
            and not connection.features.supports_length_geodetic
        ):
            raise NotSupportedError(
                "This backend doesn't support Length on geodetic fields"
            )
        return super().as_sql(compiler, connection, **extra_context)

    # [TODO] Length > as_postgresql
    def as_postgresql(self, compiler, connection, **extra_context):
        clone = self.copy()
        function = None
        if self.source_is_geography():
            clone.source_expressions.append(Value(self.spheroid))
        elif self.geo_field.geodetic(connection):
            # Geometry fields with geodetic (lon/lat) coordinates need length_spheroid
            function = connection.ops.spatial_function_name("LengthSpheroid")
            clone.source_expressions.append(Value(self.geo_field.spheroid(connection)))
        else:
            dim = min(f.dim for f in self.get_source_fields() if f)
            if dim > 2:
                function = connection.ops.length3d
        return super(Length, clone).as_sql(
            compiler, connection, function=function, **extra_context
        )

    # [TODO] Length > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        function = None
        if self.geo_field.geodetic(connection):
            function = "GeodesicLength" if self.spheroid else "GreatCircleLength"
        return super().as_sql(compiler, connection, function=function, **extra_context)


# [TODO] LineLocatePoint
class LineLocatePoint(GeoFunc):
    output_field = FloatField()
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] MakeValid
class MakeValid(GeomOutputGeoFunc):
    pass


# [TODO] MemSize
class MemSize(GeoFunc):
    output_field = IntegerField()
    arity = 1


# [TODO] NumGeometries
class NumGeometries(GeoFunc):
    output_field = IntegerField()
    arity = 1


# [TODO] NumPoints
class NumPoints(GeoFunc):
    output_field = IntegerField()
    arity = 1


# [TODO] Perimeter
class Perimeter(DistanceResultMixin, OracleToleranceMixin, GeoFunc):
    arity = 1

    # [TODO] Perimeter > as_postgresql
    def as_postgresql(self, compiler, connection, **extra_context):
        function = None
        if self.geo_field.geodetic(connection) and not self.source_is_geography():
            raise NotSupportedError(
                "ST_Perimeter cannot use a non-projected non-geography field."
            )
        dim = min(f.dim for f in self.get_source_fields())
        if dim > 2:
            function = connection.ops.perimeter3d
        return super().as_sql(compiler, connection, function=function, **extra_context)

    # [TODO] Perimeter > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        if self.geo_field.geodetic(connection):
            raise NotSupportedError("Perimeter cannot use a non-projected field.")
        return super().as_sql(compiler, connection, **extra_context)


# [TODO] PointOnSurface
class PointOnSurface(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 1


# [TODO] Reverse
class Reverse(GeoFunc):
    arity = 1


# [TODO] Scale
class Scale(SQLiteDecimalToFloatMixin, GeomOutputGeoFunc):
    # [TODO] Scale > __init__
    def __init__(self, expression, x, y, z=0.0, **extra):
        expressions = [
            expression,
            self._handle_param(x, "x", NUMERIC_TYPES),
            self._handle_param(y, "y", NUMERIC_TYPES),
        ]
        if z != 0.0:
            expressions.append(self._handle_param(z, "z", NUMERIC_TYPES))
        super().__init__(*expressions, **extra)


# [TODO] SnapToGrid
class SnapToGrid(SQLiteDecimalToFloatMixin, GeomOutputGeoFunc):
    # [TODO] SnapToGrid > __init__
    def __init__(self, expression, *args, **extra):
        nargs = len(args)
        expressions = [expression]
        if nargs in (1, 2):
            expressions.extend(
                [self._handle_param(arg, "", NUMERIC_TYPES) for arg in args]
            )
        elif nargs == 4:
            # Reverse origin and size param ordering
            expressions += [
                *(self._handle_param(arg, "", NUMERIC_TYPES) for arg in args[2:]),
                *(self._handle_param(arg, "", NUMERIC_TYPES) for arg in args[0:2]),
            ]
        else:
            raise ValueError("Must provide 1, 2, or 4 arguments to `SnapToGrid`.")
        super().__init__(*expressions, **extra)


# [TODO] SymDifference
class SymDifference(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2
    geom_param_pos = (0, 1)


# [TODO] Transform
class Transform(GeomOutputGeoFunc):
    # [TODO] Transform > __init__
    def __init__(self, expression, srid, **extra):
        expressions = [
            expression,
            self._handle_param(srid, "srid", int),
        ]
        if "output_field" not in extra:
            extra["output_field"] = GeometryField(srid=srid)
        super().__init__(*expressions, **extra)


# [TODO] Translate
class Translate(Scale):
    # [TODO] Translate > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        clone = self.copy()
        if len(self.source_expressions) < 4:
            # Always provide the z parameter for ST_Translate
            clone.source_expressions.append(Value(0))
        return super(Translate, clone).as_sqlite(compiler, connection, **extra_context)


# [TODO] Union
class Union(OracleToleranceMixin, GeomOutputGeoFunc):
    arity = 2
    geom_param_pos = (0, 1)