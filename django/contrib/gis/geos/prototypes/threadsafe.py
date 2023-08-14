import threading

from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.libgeos import CONTEXT_PTR, error_h, lgeos, notice_h


# [TODO] GEOSContextHandle
class GEOSContextHandle(GEOSBase):
    """Represent a GEOS context handle."""

    ptr_type = CONTEXT_PTR
    destructor = lgeos.finishGEOS_r

    # [TODO] GEOSContextHandle > __init__
    def __init__(self):
        # Initializing the context handler for this thread with
        # the notice and error handler.
        self.ptr = lgeos.initGEOS_r(notice_h, error_h)


# Defining a thread-local object and creating an instance
# to hold a reference to GEOSContextHandle for this thread.
# [TODO] GEOSContext
class GEOSContext(threading.local):
    handle = None


thread_context = GEOSContext()


# [TODO] GEOSFunc
class GEOSFunc:
    """
    Serve as a wrapper for GEOS C Functions. Use thread-safe function
    variants when available.
    """

    # [TODO] GEOSFunc > __init__
    def __init__(self, func_name):
        # GEOS thread-safe function signatures end with '_r' and take an
        # additional context handle parameter.
        self.cfunc = getattr(lgeos, func_name + "_r")
        # Create a reference to thread_context so it's not garbage-collected
        # before an attempt to call this object.
        self.thread_context = thread_context

    # [TODO] GEOSFunc > __call__
    def __call__(self, *args):
        # Create a context handle if one doesn't exist for this thread.
        self.thread_context.handle = self.thread_context.handle or GEOSContextHandle()
        # Call the threaded GEOS routine with the pointer of the context handle
        # as the first argument.
        return self.cfunc(self.thread_context.handle.ptr, *args)

    # [TODO] GEOSFunc > __str__
    def __str__(self):
        return self.cfunc.__name__

    # argtypes property
    # [TODO] GEOSFunc > _get_argtypes
    def _get_argtypes(self):
        return self.cfunc.argtypes

    # [TODO] GEOSFunc > _set_argtypes
    def _set_argtypes(self, argtypes):
        self.cfunc.argtypes = [CONTEXT_PTR, *argtypes]

    argtypes = property(_get_argtypes, _set_argtypes)

    # restype property
    # [TODO] GEOSFunc > _get_restype
    def _get_restype(self):
        return self.cfunc.restype

    # [TODO] GEOSFunc > _set_restype
    def _set_restype(self, restype):
        self.cfunc.restype = restype

    restype = property(_get_restype, _set_restype)

    # errcheck property
    # [TODO] GEOSFunc > _get_errcheck
    def _get_errcheck(self):
        return self.cfunc.errcheck

    # [TODO] GEOSFunc > _set_errcheck
    def _set_errcheck(self, errcheck):
        self.cfunc.errcheck = errcheck

    errcheck = property(_get_errcheck, _set_errcheck)