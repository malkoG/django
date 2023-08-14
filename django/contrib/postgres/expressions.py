from django.contrib.postgres.fields import ArrayField
from django.db.models import Subquery
from django.utils.functional import cached_property


# [TODO] ArraySubquery
class ArraySubquery(Subquery):
    template = "ARRAY(%(subquery)s)"

    # [TODO] ArraySubquery > __init__
    def __init__(self, queryset, **kwargs):
        super().__init__(queryset, **kwargs)

    # [TODO] ArraySubquery > output_field
    @cached_property
    def output_field(self):
        return ArrayField(self.query.output_field)