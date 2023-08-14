import math

from django.db.models.expressions import Func, Value
from django.db.models.fields import FloatField, IntegerField
from django.db.models.functions import Cast
from django.db.models.functions.mixins import (
    FixDecimalInputMixin,
    NumericOutputFieldMixin,
)
from django.db.models.lookups import Transform


# [TODO] Abs
class Abs(Transform):
    function = "ABS"
    lookup_name = "abs"


# [TODO] ACos
class ACos(NumericOutputFieldMixin, Transform):
    function = "ACOS"
    lookup_name = "acos"


# [TODO] ASin
class ASin(NumericOutputFieldMixin, Transform):
    function = "ASIN"
    lookup_name = "asin"


# [TODO] ATan
class ATan(NumericOutputFieldMixin, Transform):
    function = "ATAN"
    lookup_name = "atan"


# [TODO] ATan2
class ATan2(NumericOutputFieldMixin, Func):
    function = "ATAN2"
    arity = 2

    # [TODO] ATan2 > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        if not getattr(
            connection.ops, "spatialite", False
        ) or connection.ops.spatial_version >= (5, 0, 0):
            return self.as_sql(compiler, connection)
        # This function is usually ATan2(y, x), returning the inverse tangent
        # of y / x, but it's ATan2(x, y) on SpatiaLite < 5.0.0.
        # Cast integers to float to avoid inconsistent/buggy behavior if the
        # arguments are mixed between integer and float or decimal.
        # https://www.gaia-gis.it/fossil/libspatialite/tktview?name=0f72cca3a2
        clone = self.copy()
        clone.set_source_expressions(
            [
                Cast(expression, FloatField())
                if isinstance(expression.output_field, IntegerField)
                else expression
                for expression in self.get_source_expressions()[::-1]
            ]
        )
        return clone.as_sql(compiler, connection, **extra_context)


# [TODO] Ceil
class Ceil(Transform):
    function = "CEILING"
    lookup_name = "ceil"

    # [TODO] Ceil > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="CEIL", **extra_context)


# [TODO] Cos
class Cos(NumericOutputFieldMixin, Transform):
    function = "COS"
    lookup_name = "cos"


# [TODO] Cot
class Cot(NumericOutputFieldMixin, Transform):
    function = "COT"
    lookup_name = "cot"

    # [TODO] Cot > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection, template="(1 / TAN(%(expressions)s))", **extra_context
        )


# [TODO] Degrees
class Degrees(NumericOutputFieldMixin, Transform):
    function = "DEGREES"
    lookup_name = "degrees"

    # [TODO] Degrees > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template="((%%(expressions)s) * 180 / %s)" % math.pi,
            **extra_context,
        )


# [TODO] Exp
class Exp(NumericOutputFieldMixin, Transform):
    function = "EXP"
    lookup_name = "exp"


# [TODO] Floor
class Floor(Transform):
    function = "FLOOR"
    lookup_name = "floor"


# [TODO] Ln
class Ln(NumericOutputFieldMixin, Transform):
    function = "LN"
    lookup_name = "ln"


# [TODO] Log
class Log(FixDecimalInputMixin, NumericOutputFieldMixin, Func):
    function = "LOG"
    arity = 2

    # [TODO] Log > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        if not getattr(connection.ops, "spatialite", False):
            return self.as_sql(compiler, connection)
        # This function is usually Log(b, x) returning the logarithm of x to
        # the base b, but on SpatiaLite it's Log(x, b).
        clone = self.copy()
        clone.set_source_expressions(self.get_source_expressions()[::-1])
        return clone.as_sql(compiler, connection, **extra_context)


# [TODO] Mod
class Mod(FixDecimalInputMixin, NumericOutputFieldMixin, Func):
    function = "MOD"
    arity = 2


# [TODO] Pi
class Pi(NumericOutputFieldMixin, Func):
    function = "PI"
    arity = 0

    # [TODO] Pi > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection, template=str(math.pi), **extra_context
        )


# [TODO] Power
class Power(NumericOutputFieldMixin, Func):
    function = "POWER"
    arity = 2


# [TODO] Radians
class Radians(NumericOutputFieldMixin, Transform):
    function = "RADIANS"
    lookup_name = "radians"

    # [TODO] Radians > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template="((%%(expressions)s) * %s / 180)" % math.pi,
            **extra_context,
        )


# [TODO] Random
class Random(NumericOutputFieldMixin, Func):
    function = "RANDOM"
    arity = 0

    # [TODO] Random > as_mysql
    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="RAND", **extra_context)

    # [TODO] Random > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection, function="DBMS_RANDOM.VALUE", **extra_context
        )

    # [TODO] Random > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="RAND", **extra_context)

    # [TODO] Random > get_group_by_cols
    def get_group_by_cols(self):
        return []


# [TODO] Round
class Round(FixDecimalInputMixin, Transform):
    function = "ROUND"
    lookup_name = "round"
    arity = None  # Override Transform's arity=1 to enable passing precision.

    # [TODO] Round > __init__
    def __init__(self, expression, precision=0, **extra):
        super().__init__(expression, precision, **extra)

    # [TODO] Round > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        precision = self.get_source_expressions()[1]
        if isinstance(precision, Value) and precision.value < 0:
            raise ValueError("SQLite does not support negative precision.")
        return super().as_sqlite(compiler, connection, **extra_context)

    # [TODO] Round > _resolve_output_field
    def _resolve_output_field(self):
        source = self.get_source_expressions()[0]
        return source.output_field


# [TODO] Sign
class Sign(Transform):
    function = "SIGN"
    lookup_name = "sign"


# [TODO] Sin
class Sin(NumericOutputFieldMixin, Transform):
    function = "SIN"
    lookup_name = "sin"


# [TODO] Sqrt
class Sqrt(NumericOutputFieldMixin, Transform):
    function = "SQRT"
    lookup_name = "sqrt"


# [TODO] Tan
class Tan(NumericOutputFieldMixin, Transform):
    function = "TAN"
    lookup_name = "tan"