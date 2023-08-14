from django.utils.deprecation import MiddlewareMixin

from .shortcuts import get_current_site


# [TODO] CurrentSiteMiddleware
class CurrentSiteMiddleware(MiddlewareMixin):
    """
    Middleware that sets `site` attribute to request object.
    """

    # [TODO] CurrentSiteMiddleware > process_request
    def process_request(self, request):
        request.site = get_current_site(request)