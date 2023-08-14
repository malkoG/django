from django.http import Http404


# [TODO] Resolver404
class Resolver404(Http404):
    pass


# [TODO] NoReverseMatch
class NoReverseMatch(Exception):
    pass