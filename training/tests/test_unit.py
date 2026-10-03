import datetime

from django.utils import timezone
from django.urls import reverse

from pytest_django.asserts import assertFormError, assertContains, assertNotContains

from training import models
from reversion.models import Version, Revision


def test_add_qualification(admin_client, trainee, admin_user, training_item):
    url = reverse("add_qualification", kwargs={"pk": trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    response = admin_client.post(
        url, {"date": date, "trainee": trainee.pk, "supervisor": trainee.pk, "item": training_item.pk}
    )
    assertFormError(response.context["form"], "date", "Qualification date may not be in the future")
    assertFormError(response.context["form"], "supervisor", "One may not supervise oneself...")
    response = admin_client.post(
        url, {"date": date, "trainee": admin_user.pk, "supervisor": trainee.pk, "item": training_item.pk}
    )
    print(response.content)
    assertFormError(response.context["form"], "supervisor", "Selected supervisor must actually *be* a supervisor...")


def test_add_qualification_reversion(admin_client, trainee, training_item, supervisor):
    url = reverse("add_qualification", kwargs={"pk": trainee.pk})
    date = (timezone.now() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d")
    response = admin_client.post(
        url,
        {
            "date": date,
            "supervisor": supervisor.pk,
            "trainee": trainee.pk,
            "item": training_item.pk,
            "depth": 0,
            "notes": "",
        },
    )
    print(response.content)
    assert response.status_code == 302
    qual = models.TrainingItemQualification.objects.last()
    assert qual is not None
    assert training_item.pk == qual.item_id
    # Ensure only one revision has been created
    assert Revision.objects.count() == 1
    response = admin_client.post(
        url, {"date": date, "supervisor": supervisor.pk, "trainee": trainee.pk, "item": training_item.pk, "depth": 1}
    )
    assert Revision.objects.count() == 2
    assert Version.objects.count() == 4  # Two item qualifications and the trainee twice


def test_add_requirement(admin_client, level):
    url = reverse("add_requirement", kwargs={"pk": level.pk})
    response = admin_client.post(url)
    assertContains(response, level.pk)


def get_response(admin_client, url, kwargs={}):
    url = reverse(url, kwargs=kwargs)
    response = admin_client.get(url)
    assert response.status_code == 200
    return response


def test_trainee_detail(admin_client, trainee, admin_user):
    response = get_response(admin_client, "trainee_detail", {"pk": admin_user.pk})
    assertContains(response, "Your Training Record")
    assertContains(response, "No qualifications in any levels")

    response = get_response(admin_client, "trainee_detail", {"pk": trainee.pk})
    assertNotContains(response, "Your")
    assertContains(response, f"{trainee.get_full_name()}'s Training Record")


def test_trainee_item_detail(admin_client, trainee):
    response = get_response(admin_client, "trainee_item_detail", {"pk": trainee.pk})
    assertContains(response, "Nothing found")


def test_item_list(admin_client, training_item):
    response = get_response(admin_client, "item_list")
    assertContains(response, str(training_item.category))


def test_trainee_list_search(admin_client, admin_user, trainee, supervisor):
    response = get_response(admin_client, "trainee_list")
    assertContains(response, admin_user.get_full_name())
    assertContains(response, trainee.get_full_name())
    assertContains(response, supervisor.get_full_name())

    url = reverse("trainee_list")
    response = admin_client.get(url, {"q": trainee.get_full_name()})
    assertContains(response, trainee.get_full_name())
    assertNotContains(response, supervisor.get_full_name())


def _make_technician(trainee, department=models.TrainingLevel.SOUND):
    tech_level = models.TrainingLevel.objects.create(
        level=models.TrainingLevel.TECHNICIAN, department=department, description="x"
    )
    models.TrainingLevelQualification.objects.create(
        trainee=models.Trainee.objects.get(pk=trainee.pk), level=tech_level, confirmed_on=timezone.now()
    )
    return tech_level


def _technician_setup(trainee, supervisor, flag=True, department=models.TrainingLevel.SOUND):
    tech_level = _make_technician(trainee, department)
    category = models.TrainingCategory.objects.create(reference_number=6, name="Sound", training_level=tech_level)
    item = models.TrainingItem.objects.create(
        category=category, reference_number=1, name="FOH", technician_can_train=flag
    )
    today = datetime.date.today()
    models.TrainingItemQualification.objects.create(
        item=item,
        depth=models.TrainingItemQualification.PASSED_OUT,
        trainee=models.Trainee.objects.get(pk=trainee.pk),
        supervisor=models.Trainee.objects.get(pk=supervisor.pk),
        date=today,
    )
    return item


def test_technician_can_deliver_training(trainee, supervisor):
    item = _technician_setup(trainee, supervisor)
    tech = models.Trainee.objects.get(pk=trainee.pk)
    assert tech.can_deliver_training(item, models.TrainingItemQualification.COMPLETE)
    assert not tech.can_deliver_training(item, models.TrainingItemQualification.PASSED_OUT)


def test_technician_cannot_train_unflagged_item(trainee, supervisor):
    item = _technician_setup(trainee, supervisor, flag=False)
    assert not models.Trainee.objects.get(pk=trainee.pk).can_deliver_training(
        item, models.TrainingItemQualification.COMPLETE
    )


def test_technician_cannot_train_without_passout(trainee, supervisor):
    item = _technician_setup(trainee, supervisor)
    models.TrainingItemQualification.objects.filter(item=item).delete()
    assert not models.Trainee.objects.get(pk=trainee.pk).can_deliver_training(
        item, models.TrainingItemQualification.COMPLETE
    )


def test_any_technician_can_train_if_category_has_no_level(trainee, supervisor):
    item = _technician_setup(trainee, supervisor, department=models.TrainingLevel.LIGHTING)
    item.category.training_level = None
    item.category.save()
    assert models.Trainee.objects.get(pk=trainee.pk).can_deliver_training(
        item, models.TrainingItemQualification.COMPLETE
    )


def test_non_technician_cannot_train_if_category_has_no_level(trainee, supervisor):
    item = _technician_setup(trainee, supervisor)
    item.category.training_level = None
    item.category.save()
    models.TrainingLevelQualification.objects.all().delete()
    assert not models.Trainee.objects.get(pk=trainee.pk).can_deliver_training(
        item, models.TrainingItemQualification.COMPLETE
    )


def test_technician_cannot_train_other_department(trainee, supervisor):
    item = _technician_setup(trainee, supervisor, department=models.TrainingLevel.LIGHTING)
    other = models.TrainingLevel.objects.create(
        level=models.TrainingLevel.TECHNICIAN, department=models.TrainingLevel.SOUND, description="x"
    )
    item.category.training_level = other
    item.category.save()
    assert not models.Trainee.objects.get(pk=trainee.pk).can_deliver_training(
        item, models.TrainingItemQualification.COMPLETE
    )


def test_technician_session_log(client, trainee, supervisor, admin_user):
    item = _technician_setup(trainee, supervisor)
    client.force_login(trainee)
    url = reverse("session_log")
    assert client.get(url).status_code == 200
    data = {
        "trainees": [admin_user.pk],
        "items_1": [item.pk],
        "supervisor": trainee.pk,
        "date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    assert client.post(url, data).status_code == 302
    assert models.TrainingItemQualification.objects.filter(
        trainee=admin_user.pk, item=item, depth=models.TrainingItemQualification.COMPLETE
    ).exists()
    # Passing out is not allowed
    response = client.post(url, {**data, "items_1": [], "items_2": [item.pk]})
    assert response.status_code == 200
    assert "items_2" in response.context["form"].errors
    # Nor is naming someone else as the supervisor
    response = client.post(url, {**data, "supervisor": supervisor.pk})
    assert "supervisor" in response.context["form"].errors


def test_plain_trainee_cannot_log_session(client, trainee):
    client.force_login(trainee)
    assert client.get(reverse("session_log")).status_code == 403
