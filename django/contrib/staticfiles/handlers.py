from urllib.parse import urlparse
from urllib.request import url2pathname

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.staticfiles import utils
from django.contrib.staticfiles.views import serve
from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.exception import response_for_exception
from django.core.handlers.wsgi import WSGIHandler, get_path_info
from django.http import Http404


# [TODO] StaticFilesHandlerMixin
class StaticFilesHandlerMixin:
    """
    Common methods used by WSGI and ASGI handlers.
    """

    # May be used to differentiate between handler types (e.g. in a
    # request_finished signal)
    handles_files = True

    # [TODO] StaticFilesHandlerMixin > load_middleware
    def load_middleware(self):
        # Middleware are already loaded for self.application; no need to reload
        # them for self.
        pass

    # [TODO] StaticFilesHandlerMixin > get_base_url
    def get_base_url(self):
        utils.check_settings()
        return settings.STATIC_URL

    # [TODO] StaticFilesHandlerMixin > _should_handle
    def _should_handle(self, path):
        """
        Check if the path should be handled. Ignore the path if:
        * the host is provided as part of the base_url
        * the request's path isn't under the media path (or equal)
        """
        return path.startswith(self.base_url[2]) and not self.base_url[1]

    # [TODO] StaticFilesHandlerMixin > file_path
    def file_path(self, url):
        """
        Return the relative path to the media file on disk for the given URL.
        """
        relative_url = url.removeprefix(self.base_url[2])
        return url2pathname(relative_url)

    # [TODO] StaticFilesHandlerMixin > serve
    def serve(self, request):
        """Serve the request path."""
        return serve(request, self.file_path(request.path), insecure=True)

    # [TODO] StaticFilesHandlerMixin > get_response
    def get_response(self, request):
        try:
            return self.serve(request)
        except Http404 as e:
            return response_for_exception(request, e)

    # [TODO] StaticFilesHandlerMixin > get_response_async
    async def get_response_async(self, request):
        try:
            return await sync_to_async(self.serve, thread_sensitive=False)(request)
        except Http404 as e:
            return await sync_to_async(response_for_exception, thread_sensitive=False)(
                request, e
            )


# [TODO] StaticFilesHandler
class StaticFilesHandler(StaticFilesHandlerMixin, WSGIHandler):
    """
    WSGI middleware that intercepts calls to the static files directory, as
    defined by the STATIC_URL setting, and serves those files.
    """

    # [TODO] StaticFilesHandler > __init__
    def __init__(self, application):
        self.application = application
        self.base_url = urlparse(self.get_base_url())
        super().__init__()

    # [TODO] StaticFilesHandler > __call__
    def __call__(self, environ, start_response):
        if not self._should_handle(get_path_info(environ)):
            return self.application(environ, start_response)
        return super().__call__(environ, start_response)


# [TODO] ASGIStaticFilesHandler
class ASGIStaticFilesHandler(StaticFilesHandlerMixin, ASGIHandler):
    """
    ASGI application which wraps another and intercepts requests for static
    files, passing them off to Django's static file serving.
    """

    # [TODO] ASGIStaticFilesHandler > __init__
    def __init__(self, application):
        self.application = application
        self.base_url = urlparse(self.get_base_url())

    # [TODO] ASGIStaticFilesHandler > __call__
    async def __call__(self, scope, receive, send):
        # Only even look at HTTP requests
        if scope["type"] == "http" and self._should_handle(scope["path"]):
            # Serve static content
            # (the one thing super() doesn't do is __call__, apparently)
            return await super().__call__(scope, receive, send)
        # Hand off to the main app
        return await self.application(scope, receive, send)

    # [TODO] ASGIStaticFilesHandler > get_response_async
    async def get_response_async(self, request):
        response = await super().get_response_async(request)
        response._resource_closers.append(request.close)
        # FileResponse is not async compatible.
        if response.streaming and not response.is_async:
            _iterator = response.streaming_content

            async def awrapper():
                for part in await sync_to_async(list)(_iterator):
                    yield part

            response.streaming_content = awrapper()
        return response