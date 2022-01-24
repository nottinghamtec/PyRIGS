import datetime
import pytest

from django.utils import timezone
from django.urls import reverse

from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains, assertURLEqual

from training import models
from reversion.models import Version, Revision


def test_add_qualification(admin_client, trainee, admin_user):
    url = reverse('add_qualification', kwargs={'pk': trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    response = admin_client.post(url, {'date': date, 'trainee': trainee.pk, 'supervisor': trainee.pk})
    assertFormError(response, 'form', 'date', 'Qualification date may not be in the future')
    assertFormError(response, 'form', 'supervisor', 'One may not supervise oneself...')
    response = admin_client.post(url, {'date': date, 'trainee': trainee.pk, 'supervisor': admin_user.pk})
    assertFormError(response, 'form', 'supervisor', 'Selected supervisor must actually *be* a supervisor...')


def test_add_qualification_reversion(admin_client, trainee, training_item, supervisor):
    url = reverse('add_qualification', kwargs={'pk': trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d")
    response = admin_client.post(url, {'date': date, 'supervisor': supervisor.pk, 'trainee': trainee.pk, 'item': training_item.pk, 'depth': 0, 'notes': ""})
    print(response.content)
    assert response.status_code == 302
    qual = models.TrainingItemQualification.objects.last()
    assert qual is not None
    assert training_item.pk == qual.pk
    # Ensure only one revision has been created
    assert Revision.objects.count() == 1
    response = admin_client.post(url, {'date': date, 'supervisor': supervisor.pk, 'trainee': trainee.pk, 'item': training_item.pk, 'depth': 1})
    assert Revision.objects.count() == 2
    assert Version.objects.count() == 4  # Two item qualifications and the trainee twice


def test_add_requirement(admin_client, level):
    url = reverse('add_requirement', kwargs={'pk': level.pk})
    response = admin_client.post(url)
    assertContains(response, level.pk)


def test_trainee_detail(admin_client, trainee, admin_user):
    url = reverse('trainee_detail', kwargs={'pk': admin_user.pk})
    response = admin_client.get(url)
    assertContains(response, "Your Training Record")
    assertContains(response, "No qualifications in any levels")

    url = reverse('trainee_detail', kwargs={'pk': trainee.pk})
    response = admin_client.get(url)
    assertNotContains(response, "Your")
    name = trainee.first_name + " " + trainee.last_name
    assertContains(response, f"{name}'s Training Record")


def test_trainee_item_detail(admin_client, trainee):
    url = reverse('trainee_item_detail', kwargs={'pk': trainee.pk})
    response = admin_client.get(url)
    assert response.status_code == 200
    assertContains(response, "Nothing found")
