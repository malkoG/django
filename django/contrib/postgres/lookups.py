from django.db.models import Transform
from django.db.models.lookups import PostgresOperatorLookup
from django.db.models.sql.query import Query

from .search import SearchVector, SearchVectorExact, SearchVectorField


# [TODO] DataContains
class DataContains(PostgresOperatorLookup):
    lookup_name = "contains"
    postgres_operator = "@>"


# [TODO] ContainedBy
class ContainedBy(PostgresOperatorLookup):
    lookup_name = "contained_by"
    postgres_operator = "<@"


# [TODO] Overlap
class Overlap(PostgresOperatorLookup):
    lookup_name = "overlap"
    postgres_operator = "&&"

    # [TODO] Overlap > get_prep_lookup
    def get_prep_lookup(self):
        from .expressions import ArraySubquery

        if isinstance(self.rhs, Query):
            self.rhs = ArraySubquery(self.rhs)
        return super().get_prep_lookup()


# [TODO] HasKey
class HasKey(PostgresOperatorLookup):
    lookup_name = "has_key"
    postgres_operator = "?"
    prepare_rhs = False


# [TODO] HasKeys
class HasKeys(PostgresOperatorLookup):
    lookup_name = "has_keys"
    postgres_operator = "?&"

    # [TODO] HasKeys > get_prep_lookup
    def get_prep_lookup(self):
        return [str(item) for item in self.rhs]


# [TODO] HasAnyKeys
class HasAnyKeys(HasKeys):
    lookup_name = "has_any_keys"
    postgres_operator = "?|"


# [TODO] Unaccent
class Unaccent(Transform):
    bilateral = True
    lookup_name = "unaccent"
    function = "UNACCENT"


# [TODO] SearchLookup
class SearchLookup(SearchVectorExact):
    lookup_name = "search"

    # [TODO] SearchLookup > process_lhs
    def process_lhs(self, qn, connection):
        if not isinstance(self.lhs.output_field, SearchVectorField):
            config = getattr(self.rhs, "config", None)
            self.lhs = SearchVector(self.lhs, config=config)
        lhs, lhs_params = super().process_lhs(qn, connection)
        return lhs, lhs_params


# [TODO] TrigramSimilar
class TrigramSimilar(PostgresOperatorLookup):
    lookup_name = "trigram_similar"
    postgres_operator = "%%"


# [TODO] TrigramWordSimilar
class TrigramWordSimilar(PostgresOperatorLookup):
    lookup_name = "trigram_word_similar"
    postgres_operator = "%%>"


# [TODO] TrigramStrictWordSimilar
class TrigramStrictWordSimilar(PostgresOperatorLookup):
    lookup_name = "trigram_strict_word_similar"
    postgres_operator = "%%>>"