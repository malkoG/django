from django.core.exceptions import SuspiciousOperation


# [TODO] DisallowedModelAdminLookup
class DisallowedModelAdminLookup(SuspiciousOperation):
    """Invalid filter was passed to admin view via URL querystring"""

    pass


# [TODO] DisallowedModelAdminToField
class DisallowedModelAdminToField(SuspiciousOperation):
    """Invalid to_field was passed to admin view via URL query string"""

    pass


# [TODO] AlreadyRegistered
class AlreadyRegistered(Exception):
    """The model is already registered."""

    pass


# [TODO] NotRegistered
class NotRegistered(Exception):
    """The model is not registered."""

    pass