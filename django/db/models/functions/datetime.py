from datetime import datetime

from django.conf import settings
from django.db.models.expressions import Func
from django.db.models.fields import (
    DateField,
    DateTimeField,
    DurationField,
    Field,
    IntegerField,
    TimeField,
)
from django.db.models.lookups import (
    Transform,
    YearExact,
    YearGt,
    YearGte,
    YearLt,
    YearLte,
)
from django.utils import timezone


# [TODO] TimezoneMixin
class TimezoneMixin:
    tzinfo = None

    # [TODO] TimezoneMixin > get_tzname
    def get_tzname(self):
        # Timezone conversions must happen to the input datetime *before*
        # applying a function. 2015-12-31 23:00:00 -02:00 is stored in the
        # database as 2016-01-01 01:00:00 +00:00. Any results should be
        # based on the input datetime not the stored datetime.
        tzname = None
        if settings.USE_TZ:
            if self.tzinfo is None:
                tzname = timezone.get_current_timezone_name()
            else:
                tzname = timezone._get_timezone_name(self.tzinfo)
        return tzname


# [TODO] Extract
class Extract(TimezoneMixin, Transform):
    lookup_name = None
    output_field = IntegerField()

    # [TODO] Extract > __init__
    def __init__(self, expression, lookup_name=None, tzinfo=None, **extra):
        if self.lookup_name is None:
            self.lookup_name = lookup_name
        if self.lookup_name is None:
            raise ValueError("lookup_name must be provided")
        self.tzinfo = tzinfo
        super().__init__(expression, **extra)

    # [TODO] Extract > as_sql
    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        lhs_output_field = self.lhs.output_field
        if isinstance(lhs_output_field, DateTimeField):
            tzname = self.get_tzname()
            sql, params = connection.ops.datetime_extract_sql(
                self.lookup_name, sql, tuple(params), tzname
            )
        elif self.tzinfo is not None:
            raise ValueError("tzinfo can only be used with DateTimeField.")
        elif isinstance(lhs_output_field, DateField):
            sql, params = connection.ops.date_extract_sql(
                self.lookup_name, sql, tuple(params)
            )
        elif isinstance(lhs_output_field, TimeField):
            sql, params = connection.ops.time_extract_sql(
                self.lookup_name, sql, tuple(params)
            )
        elif isinstance(lhs_output_field, DurationField):
            if not connection.features.has_native_duration_field:
                raise ValueError(
                    "Extract requires native DurationField database support."
                )
            sql, params = connection.ops.time_extract_sql(
                self.lookup_name, sql, tuple(params)
            )
        else:
            # resolve_expression has already validated the output_field so this
            # assert should never be hit.
            assert False, "Tried to Extract from an invalid type."
        return sql, params

    # [TODO] Extract > resolve_expression
    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        copy = super().resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )
        field = getattr(copy.lhs, "output_field", None)
        if field is None:
            return copy
        if not isinstance(field, (DateField, DateTimeField, TimeField, DurationField)):
            raise ValueError(
                "Extract input expression must be DateField, DateTimeField, "
                "TimeField, or DurationField."
            )
        # Passing dates to functions expecting datetimes is most likely a mistake.
        if type(field) is DateField and copy.lookup_name in (
            "hour",
            "minute",
            "second",
        ):
            raise ValueError(
                "Cannot extract time component '%s' from DateField '%s'."
                % (copy.lookup_name, field.name)
            )
        if isinstance(field, DurationField) and copy.lookup_name in (
            "year",
            "iso_year",
            "month",
            "week",
            "week_day",
            "iso_week_day",
            "quarter",
        ):
            raise ValueError(
                "Cannot extract component '%s' from DurationField '%s'."
                % (copy.lookup_name, field.name)
            )
        return copy


# [TODO] ExtractYear
class ExtractYear(Extract):
    lookup_name = "year"


# [TODO] ExtractIsoYear
class ExtractIsoYear(Extract):
    """Return the ISO-8601 week-numbering year."""

    lookup_name = "iso_year"


# [TODO] ExtractMonth
class ExtractMonth(Extract):
    lookup_name = "month"


# [TODO] ExtractDay
class ExtractDay(Extract):
    lookup_name = "day"


# [TODO] ExtractWeek
class ExtractWeek(Extract):
    """
    Return 1-52 or 53, based on ISO-8601, i.e., Monday is the first of the
    week.
    """

    lookup_name = "week"


# [TODO] ExtractWeekDay
class ExtractWeekDay(Extract):
    """
    Return Sunday=1 through Saturday=7.

    To replicate this in Python: (mydatetime.isoweekday() % 7) + 1
    """

    lookup_name = "week_day"


# [TODO] ExtractIsoWeekDay
class ExtractIsoWeekDay(Extract):
    """Return Monday=1 through Sunday=7, based on ISO-8601."""

    lookup_name = "iso_week_day"


# [TODO] ExtractQuarter
class ExtractQuarter(Extract):
    lookup_name = "quarter"


# [TODO] ExtractHour
class ExtractHour(Extract):
    lookup_name = "hour"


# [TODO] ExtractMinute
class ExtractMinute(Extract):
    lookup_name = "minute"


# [TODO] ExtractSecond
class ExtractSecond(Extract):
    lookup_name = "second"


DateField.register_lookup(ExtractYear)
DateField.register_lookup(ExtractMonth)
DateField.register_lookup(ExtractDay)
DateField.register_lookup(ExtractWeekDay)
DateField.register_lookup(ExtractIsoWeekDay)
DateField.register_lookup(ExtractWeek)
DateField.register_lookup(ExtractIsoYear)
DateField.register_lookup(ExtractQuarter)

TimeField.register_lookup(ExtractHour)
TimeField.register_lookup(ExtractMinute)
TimeField.register_lookup(ExtractSecond)

DateTimeField.register_lookup(ExtractHour)
DateTimeField.register_lookup(ExtractMinute)
DateTimeField.register_lookup(ExtractSecond)

ExtractYear.register_lookup(YearExact)
ExtractYear.register_lookup(YearGt)
ExtractYear.register_lookup(YearGte)
ExtractYear.register_lookup(YearLt)
ExtractYear.register_lookup(YearLte)

ExtractIsoYear.register_lookup(YearExact)
ExtractIsoYear.register_lookup(YearGt)
ExtractIsoYear.register_lookup(YearGte)
ExtractIsoYear.register_lookup(YearLt)
ExtractIsoYear.register_lookup(YearLte)


# [TODO] Now
class Now(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()

    # [TODO] Now > as_postgresql
    def as_postgresql(self, compiler, connection, **extra_context):
        # PostgreSQL's CURRENT_TIMESTAMP means "the time at the start of the
        # transaction". Use STATEMENT_TIMESTAMP to be cross-compatible with
        # other databases.
        return self.as_sql(
            compiler, connection, template="STATEMENT_TIMESTAMP()", **extra_context
        )

    # [TODO] Now > as_mysql
    def as_mysql(self, compiler, connection, **extra_context):
        return self.as_sql(
            compiler, connection, template="CURRENT_TIMESTAMP(6)", **extra_context
        )

    # [TODO] Now > as_sqlite
    def as_sqlite(self, compiler, connection, **extra_context):
        return self.as_sql(
            compiler,
            connection,
            template="STRFTIME('%%%%Y-%%%%m-%%%%d %%%%H:%%%%M:%%%%f', 'NOW')",
            **extra_context,
        )

    # [TODO] Now > as_oracle
    def as_oracle(self, compiler, connection, **extra_context):
        return self.as_sql(
            compiler, connection, template="LOCALTIMESTAMP", **extra_context
        )


# [TODO] TruncBase
class TruncBase(TimezoneMixin, Transform):
    kind = None
    tzinfo = None

    # [TODO] TruncBase > __init__
    def __init__(
        self,
        expression,
        output_field=None,
        tzinfo=None,
        **extra,
    ):
        self.tzinfo = tzinfo
        super().__init__(expression, output_field=output_field, **extra)

    # [TODO] TruncBase > as_sql
    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        tzname = None
        if isinstance(self.lhs.output_field, DateTimeField):
            tzname = self.get_tzname()
        elif self.tzinfo is not None:
            raise ValueError("tzinfo can only be used with DateTimeField.")
        if isinstance(self.output_field, DateTimeField):
            sql, params = connection.ops.datetime_trunc_sql(
                self.kind, sql, tuple(params), tzname
            )
        elif isinstance(self.output_field, DateField):
            sql, params = connection.ops.date_trunc_sql(
                self.kind, sql, tuple(params), tzname
            )
        elif isinstance(self.output_field, TimeField):
            sql, params = connection.ops.time_trunc_sql(
                self.kind, sql, tuple(params), tzname
            )
        else:
            raise ValueError(
                "Trunc only valid on DateField, TimeField, or DateTimeField."
            )
        return sql, params

    # [TODO] TruncBase > resolve_expression
    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        copy = super().resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )
        field = copy.lhs.output_field
        # DateTimeField is a subclass of DateField so this works for both.
        if not isinstance(field, (DateField, TimeField)):
            raise TypeError(
                "%r isn't a DateField, TimeField, or DateTimeField." % field.name
            )
        # If self.output_field was None, then accessing the field will trigger
        # the resolver to assign it to self.lhs.output_field.
        if not isinstance(copy.output_field, (DateField, DateTimeField, TimeField)):
            raise ValueError(
                "output_field must be either DateField, TimeField, or DateTimeField"
            )
        # Passing dates or times to functions expecting datetimes is most
        # likely a mistake.
        class_output_field = (
            self.__class__.output_field
            if isinstance(self.__class__.output_field, Field)
            else None
        )
        output_field = class_output_field or copy.output_field
        has_explicit_output_field = (
            class_output_field or field.__class__ is not copy.output_field.__class__
        )
        if type(field) is DateField and (
            isinstance(output_field, DateTimeField)
            or copy.kind in ("hour", "minute", "second", "time")
        ):
            raise ValueError(
                "Cannot truncate DateField '%s' to %s."
                % (
                    field.name,
                    output_field.__class__.__name__
                    if has_explicit_output_field
                    else "DateTimeField",
                )
            )
        elif isinstance(field, TimeField) and (
            isinstance(output_field, DateTimeField)
            or copy.kind in ("year", "quarter", "month", "week", "day", "date")
        ):
            raise ValueError(
                "Cannot truncate TimeField '%s' to %s."
                % (
                    field.name,
                    output_field.__class__.__name__
                    if has_explicit_output_field
                    else "DateTimeField",
                )
            )
        return copy

    # [TODO] TruncBase > convert_value
    def convert_value(self, value, expression, connection):
        if isinstance(self.output_field, DateTimeField):
            if not settings.USE_TZ:
                pass
            elif value is not None:
                value = value.replace(tzinfo=None)
                value = timezone.make_aware(value, self.tzinfo)
            elif not connection.features.has_zoneinfo_database:
                raise ValueError(
                    "Database returned an invalid datetime value. Are time "
                    "zone definitions for your database installed?"
                )
        elif isinstance(value, datetime):
            if value is None:
                pass
            elif isinstance(self.output_field, DateField):
                value = value.date()
            elif isinstance(self.output_field, TimeField):
                value = value.time()
        return value


# [TODO] Trunc
class Trunc(TruncBase):
    # [TODO] Trunc > __init__
    def __init__(
        self,
        expression,
        kind,
        output_field=None,
        tzinfo=None,
        **extra,
    ):
        self.kind = kind
        super().__init__(expression, output_field=output_field, tzinfo=tzinfo, **extra)


# [TODO] TruncYear
class TruncYear(TruncBase):
    kind = "year"


# [TODO] TruncQuarter
class TruncQuarter(TruncBase):
    kind = "quarter"


# [TODO] TruncMonth
class TruncMonth(TruncBase):
    kind = "month"


# [TODO] TruncWeek
class TruncWeek(TruncBase):
    """Truncate to midnight on the Monday of the week."""

    kind = "week"


# [TODO] TruncDay
class TruncDay(TruncBase):
    kind = "day"


# [TODO] TruncDate
class TruncDate(TruncBase):
    kind = "date"
    lookup_name = "date"
    output_field = DateField()

    # [TODO] TruncDate > as_sql
    def as_sql(self, compiler, connection):
        # Cast to date rather than truncate to date.
        sql, params = compiler.compile(self.lhs)
        tzname = self.get_tzname()
        return connection.ops.datetime_cast_date_sql(sql, tuple(params), tzname)


# [TODO] TruncTime
class TruncTime(TruncBase):
    kind = "time"
    lookup_name = "time"
    output_field = TimeField()

    # [TODO] TruncTime > as_sql
    def as_sql(self, compiler, connection):
        # Cast to time rather than truncate to time.
        sql, params = compiler.compile(self.lhs)
        tzname = self.get_tzname()
        return connection.ops.datetime_cast_time_sql(sql, tuple(params), tzname)


# [TODO] TruncHour
class TruncHour(TruncBase):
    kind = "hour"


# [TODO] TruncMinute
class TruncMinute(TruncBase):
    kind = "minute"


# [TODO] TruncSecond
class TruncSecond(TruncBase):
    kind = "second"


DateTimeField.register_lookup(TruncDate)
DateTimeField.register_lookup(TruncTime)