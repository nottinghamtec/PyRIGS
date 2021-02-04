from RIGS import models
import pytest
from django.utils import timezone


@pytest.fixture(autouse=True)
def vat_rate(db):
    return models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')


@pytest.fixture()
def basic_event(db):
    return models.Event.objects.create(name="TE E1", start_date=timezone.now())
