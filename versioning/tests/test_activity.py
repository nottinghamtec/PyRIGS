import importlib
from datetime import date, timedelta
from unittest import mock

from django.apps import apps as global_apps
from django.contrib.auth.models import Permission
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from reversion import revisions as reversion
from reversion.models import Revision, Version

from RIGS import models
from assets import models as amodels
from versioning.models import RevisionAction
from versioning.versioning import RIGSVersion, activity_feed_version, get_models, revision_committed

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def saved(obj, user=None, comment=None, **changes):
    with reversion.create_revision():
        reversion.set_user(user)
        if comment:
            reversion.set_comment(comment)
        for field, value in changes.items():
            setattr(obj, field, value)
        obj.save()
    return obj


def make_event(user=None, name="Timeline Event", **kwargs):
    return saved(models.Event(name=name, start_date=date.today(), **kwargs), user)


def make_asset(user=None, **kwargs):
    status = amodels.AssetStatus.objects.get_or_create(name="Working", should_show=True)[0]
    category = amodels.AssetCategory.objects.get_or_create(name="Lighting")[0]
    defaults = {"asset_id": "1991", "description": "Spaceflower", "date_acquired": date.today()}
    return saved(amodels.Asset(status=status, category=category, **(defaults | kwargs)), user)


def login_with(client, django_user_model, *codenames, username="limited"):
    user = django_user_model.objects.create(username=username, is_approved=True, is_active=True)
    user.user_permissions.set(Permission.objects.filter(codename__in=codenames))
    client.force_login(user)
    return user


def content_of(response):
    return " ".join(response.content.decode().split())


def csv_of(response):
    return b"".join(response.streaming_content).decode()


def test_action_migration_understands_the_old_comments():
    converted = Revision.objects.create(date_created=timezone.now(), comment="Converted enquiry A ball")
    deleted = Revision.objects.create(date_created=timezone.now(), comment="Deleted enquiry A bop")
    plain = Revision.objects.create(date_created=timezone.now(), comment="Invoice voided")

    migration = importlib.import_module("versioning.migrations.0002_revisionaction")
    migration.backfill_actions(global_apps, None)

    assert RevisionAction.objects.get(revision=converted).name == "A ball"
    assert RevisionAction.objects.get(revision=deleted).name == "enquiry A bop"
    assert not RevisionAction.objects.filter(revision=plain).exists()


def test_deleting_an_invoice_is_recorded_against_the_user(admin_client, admin_user):
    event = make_event(admin_user)
    invoice = saved(models.Invoice(event=event), admin_user)
    admin_client.post(reverse("invoice_delete", kwargs={"pk": invoice.pk}))
    assert not models.Invoice.objects.filter(pk=invoice.pk).exists()

    action = RevisionAction.objects.get(kind=RevisionAction.DELETED)
    assert action.revision.user == admin_user
    assert action.name.startswith("invoice ")
    assert f"Deleted {action.name}" in content_of(admin_client.get(reverse("activity_feed")))


def test_converted_enquiries_are_not_recorded_as_deleted(admin_client):
    admin_client.post(reverse("enquiry_create"), {"name": "Maybe a ball", "start_date": "2030-05-01"})
    enquiry = models.Enquiry.objects.get()
    enquiry.organisation = models.Organisation.objects.create(name="Ball Committee")
    enquiry.save()
    admin_client.post(reverse("enquiry_convert", kwargs={"pk": enquiry.pk}))
    assert RevisionAction.objects.get().kind == RevisionAction.CONVERTED


def test_hidden_models_do_not_invalidate_the_feed(admin_user):
    before = activity_feed_version()
    with reversion.create_revision():
        admin_user.phone = "0123456"
        admin_user.save()
    assert activity_feed_version() == before
    make_event(admin_user)
    assert activity_feed_version() != before


def test_feed_version_changes_only_after_commit(admin_user, monkeypatch, django_capture_on_commit_callbacks):
    monkeypatch.setattr("versioning.versioning.on_commit", transaction.on_commit)
    version = RIGSVersion.objects.get_for_object(make_event(admin_user)).first()
    before = activity_feed_version()
    with django_capture_on_commit_callbacks(execute=True):
        revision_committed(versions=[version])
        assert activity_feed_version() == before
    assert activity_feed_version() != before


def test_cached_feed_does_no_feed_queries(admin_client, admin_user):
    for i in range(6):
        saved(models.Invoice(event=make_event(admin_user, name=f"Cached {i}")), admin_user)
    url = reverse("activity_feed")
    admin_client.get(url, **AJAX)
    with CaptureQueriesContext(connection) as queries:
        admin_client.get(url, **AJAX)
    assert not [query for query in queries if "reversion_version" in query["sql"]]


def test_feed_is_shared_by_people_who_see_the_same_things(client, django_user_model, admin_user):
    make_event(admin_user)
    login_with(client, django_user_model, "view_event", username="first")
    client.get(reverse("activity_feed"), **AJAX)
    login_with(client, django_user_model, "view_event", username="second")
    with CaptureQueriesContext(connection) as queries:
        client.get(reverse("activity_feed"), **AJAX)
    assert not [query for query in queries if "reversion_version" in query["sql"]]


def test_feed_query_count_does_not_grow_with_entries(admin_client, admin_user, django_user_model):
    def build(count, prefix):
        for i in range(count):
            user = django_user_model.objects.create(username=f"{prefix}{i}", first_name=prefix, last_name=str(i))
            event = make_event(user, name=f"{prefix} {i}")
            saved(event, user, notes="Changed", description="Also changed")

    def queries_for_cold_feed():
        with CaptureQueriesContext(connection) as queries:
            with mock.patch("versioning.views.activity_feed_version", return_value=str(len(Version.objects.all()))):
                admin_client.get(reverse("activity_feed"), **AJAX)
        return len(queries)

    build(2, "few")
    few = queries_for_cold_feed()
    build(9, "many")
    assert queries_for_cold_feed() <= few + 3


def test_popovers_do_not_render_user_text_as_html(admin_client, admin_user):
    event = make_event(admin_user, notes="before")
    saved(event, admin_user, notes="<img src=x>")
    html = admin_client.get(reverse("activity_feed")).content.decode()
    assert "&amp;lt;img src=x&amp;gt;" in html
    assert "&lt;ins" in html


def test_changes_are_badges_with_a_before_and_after_popover(admin_client, admin_user):
    event = make_event(admin_user, status=models.Event.PROVISIONAL)
    saved(event, admin_user, status=models.Event.BOOKED)
    for url in (reverse("activity_feed"), reverse("activity_table"), reverse("event_history", args=[event.pk])):
        html = admin_client.get(url).content.decode()
        assert 'class="version-badge"' in html
        assert 'data-bs-trigger="hover focus"' in html
        assert "&lt;del&gt;Provisional&lt;/del&gt;" in html
        assert "&lt;ins&gt;Booked&lt;/ins&gt;" in html
        assert "<details" not in html


def test_long_text_changes_are_trimmed_in_popovers(admin_client, admin_user):
    long_text = "unchanged words " * 40
    event = make_event(admin_user, notes=f"{long_text}old ending")
    saved(event, admin_user, notes=f"{long_text}new ending")
    assert long_text not in admin_client.get(reverse("activity_table")).content.decode()


def test_booleans_are_yes_or_no_flags_without_a_strikethrough(admin_client, admin_user):
    event = make_event(admin_user, dry_hire=False)
    saved(event, admin_user, dry_hire=True)
    html = admin_client.get(reverse("activity_table")).content.decode()
    assert "version-flag-on" in html
    assert "&lt;del" not in html.split("version-flag")[1]

    comparison = RIGSVersion.objects.get_for_object(event).first().changes.field_changes[0]
    assert (comparison.old, comparison.new) == ("No", "Yes")
    assert comparison.boolean


def test_missing_booleans_are_not_shown_as_no():
    from versioning.versioning import FieldComparison

    field = models.Event._meta.get_field("dry_hire")
    assert FieldComparison(field, None, True).old is None
    assert FieldComparison(field, False, True).old == "No"


def test_revision_comments_are_shown(admin_client, admin_user):
    event = make_event(admin_user)
    saved(event, admin_user, comment="Status changed on the Kanban", notes="x")
    for name in ("activity_feed", "activity_table"):
        assert "Status changed on the Kanban" in content_of(admin_client.get(reverse(name)))
    assert "Status changed on the Kanban" in content_of(
        admin_client.get(reverse("event_history", kwargs={"pk": event.pk}))
    )


def test_repeat_edits_are_merged_into_one_entry(admin_client, admin_user):
    event = make_event(admin_user, name="Merged Event")
    Revision.objects.update(date_created=timezone.now() - timedelta(days=2))
    saved(event, admin_user, comment="First", status=models.Event.CONFIRMED)
    saved(event, admin_user, comment="Second", status=models.Event.BOOKED)
    content = content_of(admin_client.get(reverse("activity_feed")))
    assert content.count("Merged Event") == 2
    assert "&lt;del&gt;Provisional&lt;/del&gt;" in content
    assert "&lt;ins&gt;Booked&lt;/ins&gt;" in content
    assert "Confirmed" not in content
    assert "First" in content and "Second" in content


def test_feed_loads_more_from_where_it_stopped(admin_client, django_user_model):
    for i in range(14):
        user = django_user_model.objects.create(username=f"more{i}", first_name="More", last_name=str(i))
        make_event(user, name=f"Page Event {i}")
    first = admin_client.get(reverse("activity_feed"), **AJAX).content.decode()
    assert "Page Event 13" in first and "Page Event 1<" not in first
    assert 'class="btn btn-sm btn-outline-secondary activity-load-more"' in first

    before = first.split("?before=")[1].split('"')[0].replace("%3A", ":").replace("%2B", "+")
    second = admin_client.get(reverse("activity_feed"), {"before": before}, **AJAX).content.decode()
    assert "Page Event 0" in second and "Page Event 13" not in second
    assert "activity-load-more" not in second


def test_deleted_objects_keep_their_history(admin_client, admin_user):
    asset = make_asset(admin_user)
    asset_id = asset.asset_id
    asset.delete()
    response = admin_client.get(reverse("asset_history", kwargs={"pk": asset_id}))
    assert response.status_code == 200
    assert "Deleted" in content_of(response)

    event = make_event(admin_user)
    pk = event.pk
    event.delete()
    assert admin_client.get(reverse("event_history", kwargs={"pk": pk})).status_code == 200
    assert admin_client.get(reverse("event_history", kwargs={"pk": pk + 1000})).status_code == 404


def test_ical_feed_does_not_query_versions_for_each_event(client, admin_user, django_user_model):
    for i in range(8):
        make_event(admin_user, name=f"Calendar {i}", is_rig=True)
    admin_user.api_key = admin_user.make_api_key()
    admin_user.save()
    url = reverse("ics_calendar", kwargs={"api_pk": admin_user.pk, "api_key": admin_user.api_key})
    with CaptureQueriesContext(connection) as queries:
        assert client.get(url).status_code == 200
    assert len([query for query in queries if '"reversion_version"' in query["sql"]]) <= 1


def test_every_visible_model_is_tracked_for_deletion():
    from django.db.models.signals import pre_delete

    assert all(pre_delete.has_listeners(model) for model in get_models())
