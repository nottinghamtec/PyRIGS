import datetime
import pytest

from django.utils import timezone
from django.urls import reverse

from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

from training import models


def test_add_qualification(admin_client, trainee, admin_user):
    url = reverse('add_qualification', kwargs={'pk': trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    response = admin_client.post(url, {'date': date, 'trainee': trainee.pk, 'supervisor': trainee.pk})
    assertFormError(response, 'form', 'date', 'Qualification date may not be in the future')
    assertFormError(response, 'form', 'supervisor', 'One may not supervise oneself...')
    response = admin_client.post(url, {'date': date, 'trainee': trainee.pk, 'supervisor': admin_user.pk})
    assertFormError(response, 'form', 'supervisor', 'Selected supervisor must actually *be* a supervisor...')


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
