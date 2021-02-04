from RIGS import models
import pytest


@pytest.fixture(autouse=True)
def vat_rate(db):
    return models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
