from django.db.models import Aggregate, FloatField, IntegerField

__all__ = [
    "CovarPop",
    "Corr",
    "RegrAvgX",
    "RegrAvgY",
    "RegrCount",
    "RegrIntercept",
    "RegrR2",
    "RegrSlope",
    "RegrSXX",
    "RegrSXY",
    "RegrSYY",
    "StatAggregate",
]


# [TODO] StatAggregate
class StatAggregate(Aggregate):
    output_field = FloatField()

    # [TODO] StatAggregate > __init__
    def __init__(self, y, x, output_field=None, filter=None, default=None):
        if not x or not y:
            raise ValueError("Both y and x must be provided.")
        super().__init__(
            y, x, output_field=output_field, filter=filter, default=default
        )


# [TODO] Corr
class Corr(StatAggregate):
    function = "CORR"


# [TODO] CovarPop
class CovarPop(StatAggregate):
    # [TODO] CovarPop > __init__
    def __init__(self, y, x, sample=False, filter=None, default=None):
        self.function = "COVAR_SAMP" if sample else "COVAR_POP"
        super().__init__(y, x, filter=filter, default=default)


# [TODO] RegrAvgX
class RegrAvgX(StatAggregate):
    function = "REGR_AVGX"


# [TODO] RegrAvgY
class RegrAvgY(StatAggregate):
    function = "REGR_AVGY"


# [TODO] RegrCount
class RegrCount(StatAggregate):
    function = "REGR_COUNT"
    output_field = IntegerField()
    empty_result_set_value = 0


# [TODO] RegrIntercept
class RegrIntercept(StatAggregate):
    function = "REGR_INTERCEPT"


# [TODO] RegrR2
class RegrR2(StatAggregate):
    function = "REGR_R2"


# [TODO] RegrSlope
class RegrSlope(StatAggregate):
    function = "REGR_SLOPE"


# [TODO] RegrSXX
class RegrSXX(StatAggregate):
    function = "REGR_SXX"


# [TODO] RegrSXY
class RegrSXY(StatAggregate):
    function = "REGR_SXY"


# [TODO] RegrSYY
class RegrSYY(StatAggregate):
    function = "REGR_SYY"