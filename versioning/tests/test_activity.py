import importlib
import json
from datetime import date, timedelta
from unittest import mock

import pytest
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
from training import models as training_models
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


def test_profile_versions_leave_out_credentials(admin_user):
    with reversion.create_revision():
        admin_user.phone = "0123456"
        admin_user.api_key = "secret-key"
        admin_user.save()
    fields = json.loads(Version.objects.get_for_object(admin_user).first().serialized_data)[0]["fields"]
    assert "phone" in fields
    assert not {"password", "api_key", "last_login"} & set(fields)


def test_logging_in_does_not_create_a_revision(client, django_user_model):
    user = django_user_model.objects.create_user("loginuser", password="password", is_approved=True)
    with reversion.create_revision():
        user.phone = "012"
        user.save()
    before = Revision.objects.count()
    client.post(reverse("login"), {"username": "loginuser", "password": "password"})
    user.refresh_from_db()
    assert user.last_login is not None
    assert Revision.objects.count() == before


def test_profiles_cannot_be_reverted_in_the_admin(admin_client, admin_user):
    with reversion.create_revision():
        admin_user.save()
    version = Version.objects.get_for_object(admin_user).first()
    url = reverse("admin:RIGS_profile_revision", args=[admin_user.pk, version.pk])
    assert admin_client.get(url).status_code == 403
    assert admin_client.get(reverse("admin:RIGS_profile_recoverlist")).status_code == 403


def test_scrub_migration_removes_credentials_from_old_versions(admin_user):
    with reversion.create_revision():
        admin_user.phone = "0123456"
        admin_user.save()
    version = Version.objects.get_for_object(admin_user).first()
    data = json.loads(version.serialized_data)
    data[0]["fields"].update({"password": "hash", "api_key": "key", "last_login": None})
    Version.objects.filter(pk=version.pk).update(serialized_data=json.dumps(data))

    migration = importlib.import_module("versioning.migrations.0003_scrub_profile_versions")
    migration.scrub_profile_versions(global_apps, None)

    version.refresh_from_db()
    fields = json.loads(version.serialized_data)[0]["fields"]
    assert fields["phone"] == "0123456"
    assert not {"password", "api_key", "last_login"} & set(fields)


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


def test_boolean_csv_export_says_yes_or_no(admin_client, admin_user):
    event = make_event(admin_user, dry_hire=False)
    saved(event, admin_user, dry_hire=True)
    assert "No -> Yes" in csv_of(admin_client.get(reverse("activity_table"), {"export": "csv"}))


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


def test_activity_table_filters(admin_client, admin_user, django_user_model):
    other = django_user_model.objects.create(username="other", first_name="Other", last_name="Person")
    mine = make_event(admin_user, name="Mine Rig", mic=admin_user)
    make_event(other, name="Their Rig")
    url = reverse("activity_table")

    def titles(**filters):
        return {v.object_repr for v in admin_client.get(url, filters).context["object_list"]}

    assert titles() == {str(mine), str(models.Event.objects.get(name="Their Rig"))}
    assert titles(mine="on") == {str(mine)}
    assert titles(my_events="on") == {str(mine)}
    assert titles(user=other.pk) == {str(models.Event.objects.get(name="Their Rig"))}
    assert titles(q="Mine") == {str(mine)}
    assert titles(model="person") == set()
    assert titles(start=(date.today() + timedelta(days=1)).isoformat()) == set()
    assert len(titles(end=date.today().isoformat())) == 2


def test_activity_table_filters_survive_paging(admin_client, admin_user):
    for i in range(30):
        make_event(admin_user, name=f"Paged {i}")
    content = admin_client.get(reverse("activity_table"), {"q": "Paged"}).content.decode()
    assert "q=Paged" in content.split("pagination")[1]


def test_all_activity_covers_every_app(admin_client, admin_user):
    event = make_event(admin_user, name="All Rig")
    make_asset(admin_user)
    content = content_of(admin_client.get(reverse("activity_all")))
    assert event.display_id in content and "1991" in content
    assert reverse("activity_all") in content_of(admin_client.get(reverse("index")))


def test_csv_export_applies_filters_and_neutralises_formulae(admin_client, admin_user):
    event = make_event(admin_user, name="=HYPERLINK(1)")
    saved(event, admin_user, status=models.Event.BOOKED)
    make_event(admin_user, name="Elsewhere")
    response = admin_client.get(reverse("activity_table"), {"q": "HYPERLINK", "export": "csv"})
    assert response["Content-Type"] == "text/csv"
    body = csv_of(response)
    assert "Elsewhere" not in body
    assert "Provisional -> Booked" in body
    assert ",=HYPERLINK" not in body


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


def test_event_timeline_includes_related_records(admin_client, admin_user):
    event = make_event(admin_user)
    other = make_event(admin_user, name="Unrelated")
    saved(models.Invoice(event=event), admin_user)
    saved(models.Invoice(event=other), admin_user)
    saved(
        models.EventAuthorisation(event=event, email="a@b.test", name="Auth", amount=1, sent_by=admin_user), admin_user
    )
    versions = admin_client.get(reverse("event_history", kwargs={"pk": event.pk})).context["object_list"]
    assert {version._model.__name__ for version in versions} == {"Event", "EventAuthorisation", "Invoice"}
    assert sum(version._model is models.Invoice for version in versions) == 1


def test_event_timeline_leaves_out_records_you_cannot_see(client, django_user_model, admin_user):
    event = make_event(admin_user)
    saved(models.Invoice(event=event), admin_user)
    login_with(client, django_user_model, "change_event", "view_event")
    versions = client.get(reverse("event_history", kwargs={"pk": event.pk})).context["object_list"]
    assert [version._model.__name__ for version in versions] == ["Event"]


def test_version_snapshot_and_as_of_date(admin_client, admin_user):
    event = make_event(admin_user, name="Old Name")
    Revision.objects.update(date_created=timezone.now() - timedelta(days=10))
    saved(event, admin_user, name="New Name")
    first = RIGSVersion.objects.get_for_object(event).last()

    url = reverse("event_version", kwargs={"pk": event.pk, "version_id": first.pk})
    assert "Old Name" in content_of(admin_client.get(url))

    at = (date.today() - timedelta(days=5)).isoformat()
    history = reverse("event_history", kwargs={"pk": event.pk})
    assert admin_client.get(history, {"at": at}).url == url
    too_early = (date.today() - timedelta(days=50)).isoformat()
    assert admin_client.get(history, {"at": too_early}).url == history


def test_versions_of_other_objects_cannot_be_opened(admin_client, admin_user):
    event = make_event(admin_user)
    other = RIGSVersion.objects.get_for_object(make_event(admin_user, name="Other")).first()
    url = reverse("event_version", kwargs={"pk": event.pk, "version_id": other.pk})
    assert admin_client.get(url).status_code == 404
    compare = reverse("event_compare", kwargs={"pk": event.pk})
    own = RIGSVersion.objects.get_for_object(event).first()
    assert admin_client.get(compare, {"from": own.pk, "to": other.pk}).status_code == 404
    assert admin_client.get(compare, {"from": "x", "to": own.pk}).status_code == 404


def test_compare_any_two_versions_in_either_order(admin_client, admin_user):
    event = make_event(admin_user, status=models.Event.PROVISIONAL)
    saved(event, admin_user, status=models.Event.CONFIRMED)
    saved(event, admin_user, status=models.Event.BOOKED)
    versions = list(RIGSVersion.objects.get_for_object(event).order_by("pk"))
    url = reverse("event_compare", kwargs={"pk": event.pk})
    for pair in ((versions[0], versions[2]), (versions[2], versions[0])):
        comparison = admin_client.get(url, {"from": pair[0].pk, "to": pair[1].pk}).context["comparison"]
        assert comparison.field_changes[0].old == "Provisional"
        assert comparison.field_changes[0].new == "Booked"


def test_changes_since_authorised(admin_client, admin_user):
    union = models.Organisation.objects.create(name="Union", union_account=True)
    event = make_event(admin_user, name="Before Sign Off", organisation=union)
    saved(
        models.EventAuthorisation(event=event, email="a@b.test", name="Auth", amount=1, sent_by=admin_user), admin_user
    )
    saved(event, admin_user, name="After Sign Off")
    saved(models.EventItem(event=event, name="Late Item", quantity=1, cost=1, order=1), admin_user)
    saved(event, admin_user)

    response = admin_client.get(reverse("event_since_authorised", kwargs={"pk": event.pk}), follow=True)
    content = content_of(response)
    assert "Before Sign Off" in content and "After Sign Off" in content
    assert "Late Item" in content
    assert reverse("event_since_authorised", kwargs={"pk": event.pk}) in content_of(
        admin_client.get(reverse("event_detail", kwargs={"pk": event.pk}))
    )


def test_changes_since_authorised_needs_an_authorisation(admin_client, admin_user):
    event = make_event(admin_user)
    response = admin_client.get(reverse("event_since_authorised", kwargs={"pk": event.pk}))
    assert response.url == reverse("event_history", kwargs={"pk": event.pk})


@pytest.mark.parametrize(
    "url,codename",
    [
        ("activity_table", "view_event"),
        ("activity_all", "view_event"),
        ("assets_activity_table", "view_asset"),
        ("training_activity_table", "view_trainingitemqualification"),
    ],
)
def test_activity_tables_need_the_permission_of_their_app(client, django_user_model, url, codename):
    login_with(client, django_user_model)
    assert client.get(reverse(url)).status_code == 403
    client.logout()
    login_with(client, django_user_model, codename, username="allowed")
    assert client.get(reverse(url)).status_code == 200


def test_activity_only_shows_models_you_can_view(client, django_user_model, admin_user):
    make_event(admin_user, name="Visible Rig")
    with reversion.create_revision():
        models.Person.objects.create(name="Private Person")
    login_with(client, django_user_model, "view_event")
    content = content_of(client.get(reverse("activity_feed")))
    assert "Visible Rig" in content
    assert "Private Person" not in content


def test_asset_finance_fields_are_hidden_not_the_whole_asset(client, django_user_model, admin_user):
    asset = make_asset(admin_user, purchase_price=100, nickname="Old")
    saved(asset, admin_user, purchase_price=999, nickname="New")
    login_with(client, django_user_model, "view_asset")
    table = reverse("assets_activity_table")

    content = content_of(client.get(table))
    assert "&lt;ins&gt;New&lt;/ins&gt;" in content
    assert "999" not in content
    assert "999" not in csv_of(client.get(table, {"export": "csv"}))

    client.logout()
    login_with(client, django_user_model, "view_asset", "asset_finance", username="finance")
    assert "999" in content_of(client.get(table))


def test_asset_history_hides_finance_fields(client, django_user_model, admin_user):
    asset = make_asset(admin_user, purchase_price=100)
    saved(asset, admin_user, purchase_price=999)
    login_with(client, django_user_model, "change_asset")
    assert "999" not in content_of(client.get(reverse("asset_history", kwargs={"pk": asset.asset_id})))


def test_feed_cache_separates_finance_and_non_finance_users(client, django_user_model, admin_user):
    asset = make_asset(admin_user, purchase_price=100)
    saved(asset, admin_user, purchase_price=999)
    login_with(client, django_user_model, "view_event", "view_asset", "asset_finance", username="finance")
    assert "999" in content_of(client.get(reverse("activity_feed")))
    client.logout()
    login_with(client, django_user_model, "view_event", "view_asset", username="crew")
    assert "999" not in content_of(client.get(reverse("activity_feed")))


def test_ical_feed_does_not_query_versions_for_each_event(client, admin_user, django_user_model):
    for i in range(8):
        make_event(admin_user, name=f"Calendar {i}", is_rig=True)
    admin_user.api_key = admin_user.make_api_key()
    admin_user.save()
    url = reverse("ics_calendar", kwargs={"api_pk": admin_user.pk, "api_key": admin_user.api_key})
    with CaptureQueriesContext(connection) as queries:
        assert client.get(url).status_code == 200
    assert len([query for query in queries if '"reversion_version"' in query["sql"]]) <= 1


def log_session(supervisor, trainees, items, depth=None, notes="Rigging night"):
    depth = training_models.TrainingItemQualification.PASSED_OUT if depth is None else depth
    with reversion.create_revision():
        reversion.set_user(supervisor)
        for trainee in trainees:
            for item in items:
                training_models.TrainingItemQualification.objects.create(
                    trainee=trainee, item=item, supervisor=supervisor, depth=depth, date=date.today(), notes=notes
                )


def session_people(django_user_model):
    make = django_user_model.objects.create
    supervisor = make(username="sup", first_name="Sue", last_name="Pervisor", is_approved=True, is_supervisor=True)
    trainees = [make(username=f"t{i}", first_name=f"Trainee{i}", last_name="T", is_approved=True) for i in range(3)]
    category = training_models.TrainingCategory.objects.create(reference_number=1, name="Basics")
    items = [
        training_models.TrainingItem.objects.create(reference_number=i, name=f"Skill {i}", category=category)
        for i in range(2)
    ]
    Trainee = training_models.Trainee
    return Trainee._base_manager.get(pk=supervisor.pk), [Trainee._base_manager.get(pk=t.pk) for t in trainees], items


def test_training_sessions_take_one_row(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees, items)
    response = admin_client.get(reverse("activity_all"))
    assert len(response.context["object_list"]) == 1
    assert response.context["paginator"].count == 1

    content = content_of(response)
    assert "Training session" in content
    assert "6 qualifications for 3 people in 2 items" in content
    assert "Sue Pervisor" in content
    assert "Skill 0" in content and "Trainee2 T" in content
    assert "Rigging night" in content
    assert "TrainingItemQualification" not in content
    assert "</a>," in content
    assert 'class="session-detail' in content
    assert 'aria-expanded="false"' in content
    assert 'colspan="5"' in content


def test_single_qualifications_are_readable(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees[:1], items[:1])
    content = content_of(admin_client.get(reverse("activity_all")))
    assert "Passed Out" in content and "Skill 0" in content and "Trainee0 T" in content
    assert "Sue Pervisor" in content
    assert 'class="session-detail' not in content


def test_searching_finds_individual_qualifications(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees, items)
    response = admin_client.get(reverse("activity_all"), {"q": "Skill 0"})
    assert response.context["paginator"].count == 3
    assert all(version.session["total"] == 1 for version in response.context["object_list"])


def test_export_keeps_every_qualification(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees, items)
    body = csv_of(admin_client.get(reverse("activity_all"), {"export": "csv"}))
    assert len(body.strip().splitlines()) == 7


def test_editing_a_qualification_still_shows_the_change(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees[:1], items[:1])
    qualification = training_models.TrainingItemQualification.objects.get()
    saved(qualification, supervisor, notes="Corrected")
    versions = admin_client.get(reverse("activity_all")).context["object_list"]
    assert [bool(version.session) for version in versions] == [False, True]


def test_session_rows_do_not_add_a_query_per_person(admin_client, django_user_model):
    supervisor, trainees, items = session_people(django_user_model)
    log_session(supervisor, trainees, items[:1])
    url = reverse("activity_all")
    with CaptureQueriesContext(connection) as few:
        admin_client.get(url)
    log_session(supervisor, trainees, items[1:], depth=training_models.TrainingItemQualification.COMPLETE)
    with CaptureQueriesContext(connection) as more:
        admin_client.get(url)
    assert len(more) <= len(few) + 2


def test_every_visible_model_is_tracked_for_deletion():
    from django.db.models.signals import pre_delete

    assert all(pre_delete.has_listeners(model) for model in get_models())
