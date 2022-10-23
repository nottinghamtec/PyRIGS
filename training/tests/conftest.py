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


@pytest.fixture
def supervisor(db):
    supervisor = Profile.objects.create(username="supervisor", first_name="Super", last_name="Visor",
                                        initials="SV",
                                        email="supervisor@example.com", is_supervisor=True, is_active=True, is_approved=True)
    yield supervisor
    supervisor.delete()


@pytest.fixture
def training_item(db):
    training_category = models.TrainingCategory.objects.create(reference_number=1, name="The Basics")
    training_item = models.TrainingItem.objects.create(category=training_category, reference_number=1, description="How Not To Die")
    yield training_item
    training_category.delete()
    training_item.delete()


@pytest.fixture
def training_item_2(db):
    training_category = models.TrainingCategory.objects.create(reference_number=2, name="Sound")
    training_item = models.TrainingItem.objects.create(category=training_category, reference_number=1, description="Fundamentals of Audio")
    yield training_item
    training_category.delete()
    training_item.delete()


@pytest.fixture
def level(db):
    level = models.TrainingLevel.objects.create(description="There is no description.", level=models.TrainingLevel.TECHNICIAN)
    yield level
    level.delete()
