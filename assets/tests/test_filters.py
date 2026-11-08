import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from assets import models

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


@pytest.fixture
def batch():
    return models.PATTestBatch.objects.create(original_filename="a.sss", sha256="2" * 64, file="pat/a.sss")


@pytest.fixture
def add_pat(batch):
    def add(asset, days_ago, passed=True, due_in_days=None):
        due = TODAY + datetime.timedelta(days=due_in_days) if due_in_days is not None else None
        return models.PATTestRecord.objects.create(
            batch=batch,
            asset=asset,
            tested_at=timezone.now() - datetime.timedelta(days=days_ago),
            passed=passed,
            next_full_test_date=due,
        )

    return add


@pytest.fixture
def pat_assets(make_asset, add_pat):
    overdue = make_asset("100")
    add_pat(overdue, 400, due_in_days=-35)
    in_date = make_asset("101")
    add_pat(in_date, 30, due_in_days=335)
    failed = make_asset("102")
    add_pat(failed, 400, passed=False, due_in_days=-35)
    never = make_asset("103")
    retested = make_asset("104")
    add_pat(retested, 800, due_in_days=-400)
    add_pat(retested, 10, due_in_days=355)
    newly_failed = make_asset("105")
    add_pat(newly_failed, 400, due_in_days=-35)
    add_pat(newly_failed, 10, passed=False, due_in_days=355)
    return {
        "overdue": overdue,
        "in_date": in_date,
        "failed": failed,
        "never": never,
        "retested": retested,
        "newly_failed": newly_failed,
    }


def ids(client, **params):
    response = client.get(reverse("asset_list"), params)
    assert response.status_code == 200
    return [a.asset_id for a in response.context["object_list"]]


def test_needs_pat_only_shows_overdue_assets_that_were_tested_before(admin_client, pat_assets):
    assert ids(admin_client, pat_status="needs") == ["100"]


def test_failed_pat_filter_uses_latest_result(admin_client, pat_assets):
    assert ids(admin_client, pat_status="failed") == ["102", "105"]


def test_in_date_pat_filter_uses_latest_result(admin_client, pat_assets):
    assert ids(admin_client, pat_status="in_date") == ["101", "104"]


def test_never_tested_filter(admin_client, pat_assets):
    assert ids(admin_client, pat_status="never") == ["103"]


def test_no_pat_filter_shows_everything(admin_client, pat_assets):
    assert ids(admin_client) == ["100", "101", "102", "103", "104", "105"]


def test_needs_pat_respects_hidden_statuses(admin_client, pat_assets):
    hidden = models.AssetStatus.objects.create(name="Sold", should_show=False)
    models.Asset.objects.filter(asset_id="100").update(status=hidden)
    assert ids(admin_client, pat_status="needs") == []
    assert ids(admin_client, pat_status="needs", status=hidden.pk) == ["100"]


def test_pat_status_shown_in_list(admin_client, pat_assets):
    response = admin_client.get(reverse("asset_list"))
    statuses = {a.asset_id: a.pat_status for a in response.context["object_list"]}
    assert statuses == {
        "100": models.PATTestRecord.OVERDUE,
        "101": models.PATTestRecord.IN_DATE,
        "102": models.PATTestRecord.FAILED,
        "103": models.PATTestRecord.NOT_TESTED,
        "104": models.PATTestRecord.IN_DATE,
        "105": models.PATTestRecord.FAILED,
    }
    assert b"PAT overdue" in response.content


def test_pat_status_in_list_does_not_query_per_row(admin_client, pat_assets, make_asset, add_pat):
    def count_queries():
        with CaptureQueriesContext(connection) as context:
            admin_client.get(reverse("asset_list"))
        return len(context)

    count_queries()
    before = count_queries()
    for i in range(10):
        add_pat(make_asset(f"70{i}"), 10, due_in_days=-5)
    assert count_queries() == before


def test_collection_filter(admin_client, make_asset):
    parent = make_asset("200")
    make_asset("201", parent=parent)
    make_asset("202")
    assert ids(admin_client, collection="top") == ["200", "202"]
    assert ids(admin_client, collection="child") == ["201"]
    assert ids(admin_client, collection="parent") == ["200"]


def test_supplier_filter(admin_client, make_asset):
    supplier = models.Supplier.objects.create(name="Gadgetron")
    make_asset("300", purchased_from=supplier)
    make_asset("301")
    assert ids(admin_client, supplier=supplier.pk) == ["300"]


def test_acquired_date_range(admin_client, make_asset):
    make_asset("400", date_acquired=datetime.date(2019, 6, 1))
    make_asset("401", date_acquired=datetime.date(2021, 6, 1))
    make_asset("402", date_acquired=datetime.date(2023, 6, 1))
    assert ids(admin_client, acquired_from="2020-01-01") == ["401", "402"]
    assert ids(admin_client, acquired_to="2021-12-31") == ["400", "401"]
    assert ids(admin_client, acquired_from="2020-01-01", acquired_to="2021-12-31") == ["401"]


def test_inverted_date_range_shows_error(admin_client, make_asset):
    make_asset("500")
    response = admin_client.get(reverse("asset_list"), {"acquired_from": "2022-01-01", "acquired_to": "2021-01-01"})
    assert "can't be before" in response.context["form"].errors["acquired_to"][0]
    assert list(response.context["object_list"]) == []


def test_ordering(admin_client, make_asset, add_pat):
    old = make_asset("600", date_acquired=datetime.date(2010, 1, 1), description="Zebra")
    new = make_asset("601", date_acquired=datetime.date(2024, 1, 1), description="Aardvark")
    make_asset("602", description="Mongoose")
    add_pat(old, 10, due_in_days=30)
    add_pat(new, 10, due_in_days=5)
    models.Asset.objects.filter(pk=old.pk).update(last_audited_at=timezone.now())
    assert ids(admin_client, order="-date_acquired")[0] == "601"
    assert ids(admin_client, order="date_acquired")[0] == "600"
    assert ids(admin_client, order="description") == ["601", "602", "600"]
    assert ids(admin_client, order="pat_due") == ["601", "600", "602"]
    assert ids(admin_client, order="audit")[-1] == "600"
    assert ids(admin_client, order="nonsense") == []


def test_active_filter_chips_remove_a_single_value(admin_client, category, status):
    other = models.AssetCategory.objects.create(name="Lighting")
    response = admin_client.get(
        reverse("asset_list"), {"category": [category.pk, other.pk], "pat_status": "needs", "page": 1}
    )
    chips = {c["label"]: c for c in response.context["active_filters"]}
    assert set(chips) == {"Category: Sound", "Category: Lighting", "Needs PAT (overdue)"}
    assert chips["Category: Sound"]["url"] == f"{reverse('asset_list')}?category={other.pk}&pat_status=needs"
    assert chips["Needs PAT (overdue)"]["url"] == f"{reverse('asset_list')}?category={category.pk}&category={other.pk}"
    assert response.context["advanced_count"] == 0


def test_advanced_filters_open_the_extra_panel(admin_client, make_asset):
    response = admin_client.get(reverse("asset_list"), {"collection": "top"})
    assert response.context["advanced_count"] == 1
    assert b"collapse mt-2 show" in response.content
    assert b"collapse mt-2 show" not in admin_client.get(reverse("asset_list")).content


def test_no_chips_without_filters(admin_client):
    assert admin_client.get(reverse("asset_list")).context["active_filters"] == []


def test_cable_list_uses_shared_filters(admin_client, test_cable):
    response = admin_client.get(reverse("cable_list"), {"pat_status": "never"})
    assert response.status_code == 200
    assert [a.asset_id for a in response.context["object_list"]] == ["9666"]
    assert b"id_cable_type" in response.content
    assert b"id_is_cable" not in response.content
