import datetime

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains
from reversion import revisions as reversion
from reversion.models import Version

from assets.models import Asset, AssetCategory, AssetStatus
from PyRIGS import search
from RIGS import models
from training.models import TrainingCategory, TrainingItem


def results(query, user):
    return search.hydrate(search.search(query, user), query)


def titles(query, user):
    return [str(result.object) for result in results(query, user)]


@pytest.fixture
def basic_user(db):
    user = models.Profile.objects.create(
        username="basic", first_name="Basic", last_name="User", initials="BU", is_approved=True
    )
    return user


@pytest.fixture
def today():
    return timezone.now().date()


def test_stemming_matches_other_forms_of_a_word(admin_user, today):
    models.Event.objects.create(name="Lighting rig for the ball", start_date=today)
    assert titles("lights", admin_user) == [str(models.Event.objects.get())]


def test_accents_are_ignored(admin_user):
    venue = models.Venue.objects.create(name="Café Nero")
    assert [result.object for result in results("cafe", admin_user)] == [venue]


def test_names_tolerate_typos_and_partial_words(admin_user):
    venue = models.Venue.objects.create(name="Portland Building")
    assert [result.object for result in results("Portlnd", admin_user)] == [venue]
    assert [result.object for result in results("Portl", admin_user)] == [venue]


def test_every_word_must_match(admin_user, today):
    models.Event.objects.create(name="Marquee build", start_date=today)
    models.Event.objects.create(name="Tent build", start_date=today)
    assert len(results("marquee build", admin_user)) == 1


def test_websearch_syntax(admin_user, today):
    keep = models.Event.objects.create(name="Marquee build", start_date=today)
    models.Event.objects.create(name="Marquee build", description="Cancelled by the client", start_date=today)
    tent = models.Event.objects.create(name="Tent build", start_date=today)

    assert [result.object for result in results("marquee -cancelled", admin_user)] == [keep]
    assert {result.object for result in results("marquee or tent", admin_user)} >= {keep, tent}


def test_negated_words_exclude_fuzzy_name_matches_too(admin_user):
    models.Venue.objects.create(name="Alpha Pack")
    cab = models.Venue.objects.create(name="Alpha Cab")
    assert [result.object for result in results("alpha -pack", admin_user)] == [cab]
    assert [result.object for result in results('alpha -"alpha pack"', admin_user)] == [cab]


def test_negated_words_are_not_highlighted(admin_user, today):
    models.Event.objects.create(name="Alpha build", description="Alpha in the hall, no pack down", start_date=today)
    models.Event.objects.create(name="Alpha only", start_date=today)
    result = results("alpha -pack", admin_user)[0]
    assert "<mark>Alpha</mark>" in result.title
    assert "<mark>pack</mark>" not in result.snippet.lower()


def test_a_query_of_only_negations_returns_nothing(admin_user, today):
    models.Event.objects.create(name="Anything", start_date=today)
    assert results("-pack", admin_user) == []
    assert results("-pack or -cab", admin_user) == []


@pytest.mark.parametrize(
    "query, positive, negated",
    [
        ("alpha -pack", "alpha", ["pack"]),
        ('alpha -"main stage" beta', "alpha beta", ['"main stage"']),
        ("well-known -x", "well-known", ["x"]),
        ("alpha or -pack", "alpha", ["pack"]),
        ("-pack", "", ["pack"]),
    ],
)
def test_query_parsing(query, positive, negated):
    parsed = search.ParsedQuery.parse(query)
    assert parsed.positive == positive
    assert parsed.negated == negated


def test_name_matches_rank_above_notes_matches(admin_user, today):
    in_notes = models.Event.objects.create(name="Freshers fair", notes="Bring the hazer", start_date=today)
    in_name = models.Event.objects.create(name="Hazer test", start_date=today)
    assert [result.object for result in results("hazer", admin_user)] == [in_name, in_notes]


def test_recent_events_rank_above_old_ones(admin_user, today):
    old = models.Event.objects.create(name="Summer ball", start_date=today - datetime.timedelta(days=365 * 8))
    upcoming = models.Event.objects.create(name="Summer ball", start_date=today + datetime.timedelta(days=10))
    recent = models.Event.objects.create(name="Summer ball", start_date=today - datetime.timedelta(days=100))
    assert [result.object for result in results("summer ball", admin_user)] == [upcoming, recent, old]


def test_exact_ids_come_first(admin_user, today):
    event = models.Event.objects.create(name="Some event", start_date=today)
    models.Person.objects.create(name=f"Person N{event.pk:05d}")
    assert results(f"N{event.pk:05d}", admin_user)[0].object == event


def test_asset_and_training_item_ids(admin_user):
    asset = Asset.objects.create(
        asset_id="X101",
        description="Wireless microphone",
        category=AssetCategory.objects.create(name="Sound"),
        status=AssetStatus.objects.create(name="In Service", should_show=True),
        date_acquired=datetime.date(2020, 1, 1),
    )
    category = TrainingCategory.objects.create(reference_number=7, name="Rigging")
    item = TrainingItem.objects.create(reference_number=3, category=category, name="Truss")
    assert results("x101", admin_user)[0].object == asset
    assert results("7.3", admin_user)[0].object == item


def test_invoices_only_shown_to_finance(admin_user, basic_user, today):
    event = models.Event.objects.create(name="Invoiced gig", start_date=today)
    invoice = models.Invoice.objects.create(event=event)
    assert invoice in [result.object for result in results("invoiced", admin_user)]
    assert invoice not in [result.object for result in results("invoiced", basic_user)]


def test_trainees_are_searchable(admin_user):
    assert admin_user.pk in [
        result.object.pk for result in results("Event Test", admin_user) if result.kind == "trainee"
    ]


def test_empty_query_returns_nothing(admin_user, today):
    models.Event.objects.create(name="Anything", start_date=today)
    assert results("", admin_user) == []
    assert results("   ", admin_user) == []


def test_highlights_matches_and_escapes_everything_else(admin_user, today):
    models.Event.objects.create(
        name="<script>alert(1)</script> Hazer gig", description="We need <b>the</b> hazer", start_date=today
    )
    result = results("hazer", admin_user)[0]
    assert "<mark>Hazer</mark>" in result.title
    assert "&lt;script&gt;" in result.title
    assert "<script>" not in result.title
    assert "<b>" not in result.snippet
    assert "<mark>hazer</mark>" in result.snippet


def test_search_page_escapes_the_query(admin_client):
    response = admin_client.get(reverse("search"), {"q": "<script>alert(1)</script>"})
    assertNotContains(response, "<script>alert(1)</script>")
    assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")


def test_search_page_paginates_in_the_database(admin_client, today):
    models.Event.objects.bulk_create([models.Event(name=f"Pantomime night {i}", start_date=today) for i in range(25)])
    response = admin_client.get(reverse("search"), {"q": "pantomime"})
    assert response.context["count"] == 25
    assert len(response.context["object_list"]) == 20
    response = admin_client.get(reverse("search"), {"q": "pantomime", "page": 2})
    assert len(response.context["object_list"]) == 5


def test_search_page_shows_scores_to_superusers_only(admin_client, client, basic_user, today):
    models.Event.objects.create(name="Pantomime", start_date=today)
    assertContains(admin_client.get(reverse("search"), {"q": "pantomime"}), 'title="Search score"')
    client.force_login(basic_user)
    assertNotContains(client.get(reverse("search"), {"q": "pantomime"}), 'title="Search score"')


@pytest.mark.django_db(transaction=True)
def test_did_you_mean(admin_client):
    models.Venue.objects.create(name="Portland Building")
    models.Event.objects.create(name="Graduation ball", start_date=timezone.now().date())
    call_command("refresh_search_vocabulary")

    assert search.suggest("Graduaton ball at Portlnd") == "graduation ball at portland"
    assert search.suggest("graduation ball") is None
    assert search.suggest("qwxzvy") is None

    response = admin_client.get(reverse("search"), {"q": "graduaton"})
    assert response.context["suggestion"] == "graduation"
    assertContains(response, "Did you mean")


def test_refresh_command_reports_vocabulary_size(capsys, today):
    models.Event.objects.create(name="Unique wordington", start_date=today)
    call_command("refresh_search_vocabulary")
    assert "Search vocabulary now holds" in capsys.readouterr().out


def test_search_vector_is_not_stored_in_revisions(admin_user, today):
    with reversion.create_revision():
        event = models.Event.objects.create(name="Versioned", start_date=today)
    version = Version.objects.get_for_object(event).get()
    assert "search_vector" not in version.serialized_data


def test_event_picker_finds_events_by_text_and_exact_id(admin_client, today):
    ball = models.Event.objects.create(
        name="Boat Club Ball", start_date=today, organisation=models.Organisation.objects.create(name="Boat Club")
    )
    models.Event.objects.create(name="Something else", start_date=today, organisation=models.Organisation.objects.get())
    url = reverse("api_secure", kwargs={"model": "event"})
    by_text = admin_client.get(url, {"q": "boat ball"}).json()
    assert [r["pk"] for r in by_text] == [ball.pk]
    assert by_text[0]["text"].startswith(f"N{ball.pk:05d} | Boat Club Ball")
    assert by_text[0]["text"].endswith("- Boat Club")
    for query in (str(ball.pk), f"N{ball.pk:05d}"):
        assert [r["pk"] for r in admin_client.get(url, {"q": query}).json()][0] == ball.pk
