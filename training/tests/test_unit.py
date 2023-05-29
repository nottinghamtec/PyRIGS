import datetime
import pytest

from django.utils import timezone
from django.urls import reverse

from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains, assertURLEqual

from training import models
from reversion.models import Version, Revision


def test_add_qualification(admin_client, trainee, admin_user, training_item):
    url = reverse('add_qualification', kwargs={'pk': trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    response = admin_client.post(url, {'date': date, 'trainee': trainee.pk, 'supervisor': trainee.pk, 'item': training_item.pk})
    assertFormError(response, 'form', 'date', 'Qualification date may not be in the future')
    assertFormError(response, 'form', 'supervisor', 'One may not supervise oneself...')
    response = admin_client.post(url, {'date': date, 'trainee': admin_user.pk, 'supervisor': trainee.pk, 'item': training_item.pk})
    print(response.content)
    assertFormError(response, 'form', 'supervisor', 'Selected supervisor must actually *be* a supervisor...')


def test_add_qualification_reversion(admin_client, trainee, training_item, supervisor):
    url = reverse('add_qualification', kwargs={'pk': trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d")
    response = admin_client.post(url, {'date': date, 'supervisor': supervisor.pk, 'trainee': trainee.pk, 'item': training_item.pk, 'depth': 0, 'notes': ""})
    print(response.content)
    assert response.status_code == 302
    qual = models.TrainingItemQualification.objects.last()
    assert qual is not None
    assert training_item.pk == qual.item_id
    # Ensure only one revision has been created
    assert Revision.objects.count() == 1
    response = admin_client.post(url, {'date': date, 'supervisor': supervisor.pk, 'trainee': trainee.pk, 'item': training_item.pk, 'depth': 1})
    assert Revision.objects.count() == 2
    assert Version.objects.count() == 4  # Two item qualifications and the trainee twice


def test_add_requirement(admin_client, level):
    url = reverse('add_requirement', kwargs={'pk': level.pk})
    response = admin_client.post(url)
    assertContains(response, level.pk)


def get_response(admin_client, url, kwargs={}):
    url = reverse(url, kwargs=kwargs)
    response = admin_client.get(url)
    assert response.status_code == 200
    return response


def test_trainee_detail(admin_client, trainee, admin_user):
    response = get_response(admin_client, 'trainee_detail', {'pk': admin_user.pk})
    assertContains(response, "Your Training Record")
    assertContains(response, "No qualifications in any levels")

    response = get_response(admin_client, 'trainee_detail', {'pk': trainee.pk})
    assertNotContains(response, "Your")
    assertContains(response, f"{trainee.get_full_name()}'s Training Record")


def test_trainee_item_detail(admin_client, trainee):
    response = get_response(admin_client, 'trainee_item_detail', {'pk': trainee.pk})
    assertContains(response, "Nothing found")


def test_item_list(admin_client, training_item):
    response = get_response(admin_client, 'item_list')
    assertContains(response, str(training_item.category))


def test_trainee_list_search(admin_client, admin_user, trainee, supervisor):
    response = get_response(admin_client, 'trainee_list')
    assertContains(response, admin_user.get_full_name())
    assertContains(response, trainee.get_full_name())
    assertContains(response, supervisor.get_full_name())

    url = reverse('trainee_list')
    response = admin_client.get(url, {'q': trainee.get_full_name()})
    assertContains(response, trainee.get_full_name())
    assertNotContains(response, supervisor.get_full_name())
