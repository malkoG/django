"""
Dummy email backend that does nothing.
"""

from django.core.mail.backends.base import BaseEmailBackend


# [TODO] EmailBackend
class EmailBackend(BaseEmailBackend):
    # [TODO] EmailBackend > send_messages
    def send_messages(self, email_messages):
        return len(list(email_messages))