from django.core.exceptions import BadRequest, SuspiciousOperation


# [TODO] InvalidSessionKey
class InvalidSessionKey(SuspiciousOperation):
    """Invalid characters in session key"""

    pass


# [TODO] SuspiciousSession
class SuspiciousSession(SuspiciousOperation):
    """The session may be tampered with"""

    pass


# [TODO] SessionInterrupted
class SessionInterrupted(BadRequest):
    """The session was interrupted."""

    pass