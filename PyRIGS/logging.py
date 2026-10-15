import logging

from django.core.exceptions import DisallowedHost


class SkipDisallowedHost(logging.Filter):
    """Drop log records caused by requests with an invalid Host header"""

    def filter(self, record):
        exc_info = record.exc_info
        return not (exc_info and isinstance(exc_info[1], DisallowedHost))
