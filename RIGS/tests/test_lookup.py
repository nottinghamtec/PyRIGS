import pytest
from django.urls import reverse

from RIGS import models


@pytest.fixture
def api_user(admin_user):
    admin_user.api_key = "k3y"
    admin_user.save()
    return admin_user


def get(client, user, kind, key="k3y", **params):
    return client.get(
        reverse("lookup", kwargs={"kind": kind}), params, headers={"Authorization": f"Bearer {user.pk}:{key}"}
    )


@pytest.fixture
def data(db):
    models.Venue.objects.create(name="The Barn - SB", address="Sutton Bonington\nLE12 5RD")
    models.Venue.objects.create(name="The Barn - UP")
    models.Venue.objects.create(name="Great Hall - UP")
    models.Organisation.objects.create(name="Nottingham New Theatre", email="info@newtheatre.org.uk")
    person = models.Person.objects.create(name="Pat Person", email="Pat@Example.com")
    org = models.Organisation.objects.create(name="Boat Club")
    models.Event.objects.create(name="E", start_date="2026-01-01", person=person, organisation=org)


def test_requires_valid_key(client, api_user, data):
    assert client.get(reverse("lookup", kwargs={"kind": "venues"}), {"q": "barn"}).status_code == 403
    assert get(client, api_user, "venues", key="wrong", q="barn").status_code == 403
    assert get(client, api_user, "venues", q="barn").status_code == 200


def test_empty_api_key_never_matches(client, admin_user, data):
    assert admin_user.api_key == ""
    assert get(client, admin_user, "venues", key="", q="barn").status_code == 403


def test_needs_view_permission(client, django_user_model, data):
    user = django_user_model.objects.create_user("plain", password="x", is_approved=True, api_key="abc")
    assert get(client, user, "venues", key="abc", q="barn").status_code == 403


def test_venue_search_ranks_and_ignores_stopwords(client, api_user, data):
    names = [r["name"] for r in get(client, api_user, "venues", q="the barn").json()["results"]]
    assert set(names) == {"The Barn - SB", "The Barn - UP"}
    assert get(client, api_user, "venues", q="great hall").json()["results"][0]["name"] == "Great Hall - UP"
    assert get(client, api_user, "venues", q="zzz").json()["results"] == []


def test_venue_result_shape(client, api_user, data):
    result = get(client, api_user, "venues", q="barn sb").json()["results"][0]
    assert result["name"] == "The Barn - SB"
    assert result["address"] == "Sutton Bonington LE12 5RD"


def test_organisation_search_and_email_match(client, api_user, data):
    assert (
        get(client, api_user, "organisations", q="new theatre").json()["results"][0]["name"] == "Nottingham New Theatre"
    )
    by_email = get(client, api_user, "organisations", email="INFO@newtheatre.org.uk").json()["results"]
    assert [r["name"] for r in by_email] == ["Nottingham New Theatre"]


def test_people_by_email_includes_usual_organisations(client, api_user, data):
    results = get(client, api_user, "people", email="pat@example.com").json()["results"]
    assert results[0]["name"] == "Pat Person"
    assert results[0]["organisations"] == ["Boat Club"]


def test_bad_requests(client, api_user, data):
    assert get(client, api_user, "venues").status_code == 400
    assert get(client, api_user, "widgets", q="x").status_code == 404
    assert get(client, api_user, "venues", email="a@b.com").status_code == 400


def test_events_for_the_same_client_are_found_most_recent_first_without_cancelled(client, api_user, data):
    org = models.Organisation.objects.get(name="Boat Club")
    models.Event.objects.create(name="Boat Club Ball 2025", start_date="2025-03-14", organisation=org)
    models.Event.objects.create(
        name="Boat Club Dinner", start_date="2025-05-01", organisation=org, status=models.Event.CANCELLED
    )
    models.Event.objects.create(name="Unrelated Gig", start_date="2025-03-20", person=models.Person.objects.first())
    results = get(client, api_user, "events", organisation_id=org.pk).json()["results"]
    assert [r["name"] for r in results] == ["E", "Boat Club Ball 2025"]
    assert results[1]["organisation"] == "Boat Club"
    assert results[1]["start_date"] == "2025-03-14"


def test_events_can_be_found_by_text(client, api_user, data):
    models.Event.objects.create(name="Summer Ball", start_date="2025-06-20", person=models.Person.objects.first())
    names = [r["name"] for r in get(client, api_user, "events", q="summer ball").json()["results"]]
    assert names == ["Summer Ball"]


def test_events_need_a_filter(client, api_user, data):
    assert get(client, api_user, "events").status_code == 400
