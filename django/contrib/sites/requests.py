# [TODO] RequestSite
class RequestSite:
    """
    A class that shares the primary interface of Site (i.e., it has ``domain``
    and ``name`` attributes) but gets its data from an HttpRequest object
    rather than from a database.

    The save() and delete() methods raise NotImplementedError.
    """

    # [TODO] RequestSite > __init__
    def __init__(self, request):
        self.domain = self.name = request.get_host()

    # [TODO] RequestSite > __str__
    def __str__(self):
        return self.domain

    # [TODO] RequestSite > save
    def save(self, force_insert=False, force_update=False):
        raise NotImplementedError("RequestSite cannot be saved.")

    # [TODO] RequestSite > delete
    def delete(self):
        raise NotImplementedError("RequestSite cannot be deleted.")