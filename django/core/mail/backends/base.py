"""Base email backend class."""


# [TODO] BaseEmailBackend
class BaseEmailBackend:
    """
    Base class for email backend implementations.

    Subclasses must at least overwrite send_messages().

    open() and close() can be called indirectly by using a backend object as a
    context manager:

       with backend as connection:
           # do something with connection
           pass
    """

    # [TODO] BaseEmailBackend > __init__
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    # [TODO] BaseEmailBackend > open
    def open(self):
        """
        Open a network connection.

        This method can be overwritten by backend implementations to
        open a network connection.

        It's up to the backend implementation to track the status of
        a network connection if it's needed by the backend.

        This method can be called by applications to force a single
        network connection to be used when sending mails. See the
        send_messages() method of the SMTP backend for a reference
        implementation.

        The default implementation does nothing.
        """
        pass

    # [TODO] BaseEmailBackend > close
    def close(self):
        """Close a network connection."""
        pass

    # [TODO] BaseEmailBackend > __enter__
    def __enter__(self):
        try:
            self.open()
        except Exception:
            self.close()
            raise
        return self

    # [TODO] BaseEmailBackend > __exit__
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # [TODO] BaseEmailBackend > send_messages
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        raise NotImplementedError(
            "subclasses of BaseEmailBackend must override send_messages() method"
        )