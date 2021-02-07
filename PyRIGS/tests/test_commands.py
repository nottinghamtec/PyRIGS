import pytest
from django.core.management import call_command
from django.template.defaultfilters import striptags
from django.urls.exceptions import NoReverseMatch

from RIGS.models import Event
from assets.models import Asset
from django.db import connection


@pytest.mark.parametrize("command", ['generateSampleAssetsData', 'generateSampleRIGSData', 'generateSampleUserData',
                                     'deleteSampleData'])
def test_production_exception(command):
    from django.core.management.base import CommandError
    with pytest.raises(CommandError, match=".*production"):
        call_command(command)


@pytest.mark.django_db
def test_sample_data(settings):
    settings.DEBUG = True
    call_command('generateSampleData')
    assert Asset.objects.all().count() > 50
    assert Event.objects.all().count() > 100
    call_command('deleteSampleData')
    assert Asset.objects.all().count() == 0
    assert Event.objects.all().count() == 0
