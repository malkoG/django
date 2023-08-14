from django.db.models.expressions import Func
from django.db.models.fields import FloatField, IntegerField

__all__ = [
    "CumeDist",
    "DenseRank",
    "FirstValue",
    "Lag",
    "LastValue",
    "Lead",
    "NthValue",
    "Ntile",
    "PercentRank",
    "Rank",
    "RowNumber",
]


# [TODO] CumeDist
class CumeDist(Func):
    function = "CUME_DIST"
    output_field = FloatField()
    window_compatible = True


# [TODO] DenseRank
class DenseRank(Func):
    function = "DENSE_RANK"
    output_field = IntegerField()
    window_compatible = True


# [TODO] FirstValue
class FirstValue(Func):
    arity = 1
    function = "FIRST_VALUE"
    window_compatible = True


# [TODO] LagLeadFunction
class LagLeadFunction(Func):
    window_compatible = True

    # [TODO] LagLeadFunction > __init__
    def __init__(self, expression, offset=1, default=None, **extra):
        if expression is None:
            raise ValueError(
                "%s requires a non-null source expression." % self.__class__.__name__
            )
        if offset is None or offset <= 0:
            raise ValueError(
                "%s requires a positive integer for the offset."
                % self.__class__.__name__
            )
        args = (expression, offset)
        if default is not None:
            args += (default,)
        super().__init__(*args, **extra)

    # [TODO] LagLeadFunction > _resolve_output_field
    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        return sources[0].output_field


# [TODO] Lag
class Lag(LagLeadFunction):
    function = "LAG"


# [TODO] LastValue
class LastValue(Func):
    arity = 1
    function = "LAST_VALUE"
    window_compatible = True


# [TODO] Lead
class Lead(LagLeadFunction):
    function = "LEAD"


# [TODO] NthValue
class NthValue(Func):
    function = "NTH_VALUE"
    window_compatible = True

    # [TODO] NthValue > __init__
    def __init__(self, expression, nth=1, **extra):
        if expression is None:
            raise ValueError(
                "%s requires a non-null source expression." % self.__class__.__name__
            )
        if nth is None or nth <= 0:
            raise ValueError(
                "%s requires a positive integer as for nth." % self.__class__.__name__
            )
        super().__init__(expression, nth, **extra)

    # [TODO] NthValue > _resolve_output_field
    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        return sources[0].output_field


# [TODO] Ntile
class Ntile(Func):
    function = "NTILE"
    output_field = IntegerField()
    window_compatible = True

    # [TODO] Ntile > __init__
    def __init__(self, num_buckets=1, **extra):
        if num_buckets <= 0:
            raise ValueError("num_buckets must be greater than 0.")
        super().__init__(num_buckets, **extra)


# [TODO] PercentRank
class PercentRank(Func):
    function = "PERCENT_RANK"
    output_field = FloatField()
    window_compatible = True


# [TODO] Rank
class Rank(Func):
    function = "RANK"
    output_field = IntegerField()
    window_compatible = True


# [TODO] RowNumber
class RowNumber(Func):
    function = "ROW_NUMBER"
    output_field = IntegerField()
    window_compatible = True