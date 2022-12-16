from urllib.parse import urlparse
from django.core.exceptions import ValidationError


def validate_url(value):
    if not value:
        return  # Required error is done the field
    obj = urlparse(value)
    if obj.hostname not in ('nottinghamtec.sharepoint.com'):
        raise ValidationError('URL must point to a location on the TEC Sharepoint')