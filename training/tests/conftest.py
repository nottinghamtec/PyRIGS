import pytest
from training import models
from RIGS.models import Profile

@pytest.fixture
def trainee(db):
    trainee = Profile.objects.create(username="trainee", first_name="Train", last_name="EE",
                                                initials="TRN",
                                                email="trainee@example.com", is_active=True, is_approved=True)
    yield trainee
    trainee.delete()
