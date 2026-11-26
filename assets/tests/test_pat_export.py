import datetime
import json
from io import BytesIO

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from assets import models, pat, pat_export
from assets.tests import sss_builder as b
from RIGS.models import Organisation

pytestmark = pytest.mark.django_db


def when(day):
    return datetime.datetime(2025, 11, day, 10, 0, 0)


def result(day, asset_id="4334", **kwargs):
    return b.test_result(asset_id=asset_id, tested_at=when(day), **kwargs)


def upload(client, name, *results):
    client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, b.sss_file(*results))})
    return models.PATTestBatch.objects.get(original_filename=name)


@pytest.fixture
def uploads(admin_client, pat_asset, make_asset):
    make_asset("5555", description="Smoke machine", serial_number="SN-998877")
    first = upload(admin_client, "ours.sss", result(1), result(2), result(3, "5555"))
    second = upload(
        admin_client,
        "theirs.sss",
        result(4, "BAND 1", operator="Zed"),
        result(5, "BAND 1", passed=False, steps=[b.polarity(False)]),
        result(6, "BAND 10"),
    )
    return first, second


@pytest.fixture
def organisation(db):
    return Organisation.objects.create(
        name="Rock & <Roll> Society",
        address="12 Gig Street\nNottingham",
        email="band@example.com",
        phone="0115 000 0000",
        notes="Secret note",
    )


def search(client, **params):
    response = client.get(reverse("pat_export_assets"), params)
    assert response.status_code == 200, response.content
    return response.json()


def found(client, **params):
    return [asset["id"] for asset in search(client, **params)["assets"]]


def keys(client, asset_id):
    asset = search(client, id=asset_id)["assets"][0]
    return [test["key"] for test in asset["tests"]]


def export(client, organisation, selection, detail="simple"):
    return client.post(
        reverse("pat_export"),
        {
            "organisation": organisation.pk if organisation else "",
            "detail": detail,
            "selection": json.dumps(selection),
        },
    )


def pages(response):
    assert response.status_code == 200, response.content
    assert response["Content-Type"] == "application/pdf"
    return [page.extract_text() for page in PdfReader(BytesIO(response.content)).pages]


def chosen(asset_id, mode="latest", tests=()):
    return {"id": asset_id, "mode": mode, "tests": list(tests)}


def test_search_lists_every_asset_with_results_whether_or_not_it_is_in_rigs(admin_client, uploads):
    data = search(admin_client)
    assert [(a["id"], a["in_rigs"]) for a in data["assets"]] == [
        ("4334", True),
        ("5555", True),
        ("BAND 1", False),
        ("BAND 10", False),
    ]
    assert data["total"] == 4
    band = data["assets"][2]
    assert [test["passed"] for test in band["tests"]] == [False, True]
    assert band["location"] == "Storeroom, TEC PA"
    assert band["tests"][0]["upload"] == "theirs.sss"


def test_assets_without_results_are_not_listed(admin_client, uploads, make_asset):
    make_asset("7000")
    assert "7000" not in found(admin_client)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("smoke", ["5555"]),
        ("sn-9988", ["5555"]),
        ("band", ["BAND 1", "BAND 10"]),
        ("band 10", ["BAND 10"]),
        ("storeroom smoke", ["5555"]),
        ("BAND 10, 4334, nothing", ["BAND 10", "4334"]),
        ("band 1\n5555", ["BAND 1", "5555"]),
        ("nothing", []),
    ],
)
def test_search_text(admin_client, uploads, query, expected):
    assert found(admin_client, q=query) == expected


def test_an_exact_id_comes_first(admin_client, uploads, make_asset):
    make_asset("1BAND")
    upload(admin_client, "more.sss", result(7, "1BAND"))
    assert found(admin_client, q="band")[-1] == "1BAND"


def test_search_filters(admin_client, uploads):
    first, second = uploads
    assert found(admin_client, upload=second.pk) == ["BAND 1", "BAND 10"]
    assert found(admin_client, source="rigs") == ["4334", "5555"]
    assert found(admin_client, source="other") == ["BAND 1", "BAND 10"]
    assert found(admin_client, tested_from="2025-11-03", tested_to="2025-11-04") == ["5555", "BAND 1"]


def test_a_filtered_search_still_offers_all_of_an_assets_tests(admin_client, uploads):
    asset = search(admin_client, tested_to="2025-11-01")["assets"][0]
    assert [test["tested"] for test in asset["tests"]] == ["02/11/2025 10:00", "01/11/2025 10:00"]


def test_search_pages_and_can_return_everything(admin_client, uploads, monkeypatch):
    monkeypatch.setattr("assets.views.PATExportAssets.page_size", 3)
    assert len(search(admin_client)["assets"]) == 3
    assert found(admin_client, offset=3) == ["BAND 10"]
    assert len(search(admin_client, all=1)["assets"]) == 4


def test_a_bad_search_is_reported(admin_client, uploads):
    response = admin_client.get(reverse("pat_export_assets"), {"tested_from": "not a date"})
    assert response.status_code == 400


def test_suppressed_results_are_not_offered(admin_client, uploads, admin_user):
    for record in models.PATTestRecord.objects.filter(asset__asset_id="4334").order_by("-tested_at"):
        assert len(keys(admin_client, "4334"))
        pat.suppress_result(record, admin_user, "Wrong asset")
    assert "4334" not in found(admin_client)


def test_results_recorded_and_unmatched_under_one_id_are_listed_together(admin_client, uploads, make_asset):
    upload(admin_client, "before.sss", result(10, "7100"))
    make_asset("7100")
    upload(admin_client, "later.sss", result(20, "7100"))
    asset = search(admin_client, id="7100")["assets"][0]
    assert [test["key"][0] for test in asset["tests"]] == ["r", "u"]


def test_latest_all_and_chosen_tests(admin_client, uploads):
    selection = pat_export.validate_selection(
        [
            chosen("4334"),
            chosen("BAND 1", "all"),
            chosen("5555", "custom", keys(admin_client, "5555")),
        ]
    )
    assets = pat_export.resolve_selection(selection)
    assert [(a["asset_id"], [timezone.localtime(t.tested_at).day for t in a["tests"]]) for a in assets] == [
        ("4334", [2]),
        ("5555", [3]),
        ("BAND 1", [5, 4]),
    ]


def test_simple_export(admin_client, admin_user, uploads, organisation):
    response = export(admin_client, organisation, [chosen("4334"), chosen("BAND 1", "all")])
    text = "\n".join(pages(response))
    assert "attachment" in response["Content-Disposition"]
    assert "Rock & <Roll> Society" in text
    for expected in ("12 Gig Street", "band@example.com", "0115 000 0000", admin_user.name, "BAND 1", "Zed"):
        assert expected in text
    assert "02/11/2025" in text
    assert "01/11/2025" not in text
    assert "Secret note" not in text
    assert "Electrical tests" not in text


def test_detailed_export_starts_each_asset_on_its_own_page(admin_client, uploads, organisation):
    response = export(admin_client, organisation, [chosen("5555"), chosen("BAND 1", "all")], "detailed")
    summary, smoke, band, *rest = pages(response)
    assert "Summary" in summary
    assert "Asset 5555" in smoke and "Smoke machine" in smoke and "SN-998877" in smoke
    assert "Asset BAND 1" not in smoke
    assert "Asset BAND 1" in band
    assert "Electrical tests" in smoke
    assert "Polarity failed" in band + "".join(rest)


def test_export_works_for_an_organisation_with_only_a_name(admin_client, uploads):
    organisation = Organisation.objects.create(name="Bare")
    assert "Bare" in pages(export(admin_client, organisation, [chosen("4334")]))[0]


@pytest.mark.parametrize(
    "selection,message",
    [
        ([], "Select at least one asset"),
        ("nonsense", "couldn't be understood"),
        ([{"id": "4334", "mode": "some"}], "couldn't be understood"),
        ([chosen("4334", "custom")], "Choose at least one test"),
        ([chosen("4334", "custom", ["r999999"])], "have changed"),
        ([chosen("GONE")], "no longer any results for GONE"),
    ],
)
def test_bad_selections_are_refused(admin_client, uploads, organisation, selection, message):
    response = export(admin_client, organisation, selection)
    assert response.status_code == 400
    assert message in " ".join(response.json()["errors"])


def test_another_assets_test_cannot_be_chosen(admin_client, uploads, organisation):
    response = export(admin_client, organisation, [chosen("4334", "custom", keys(admin_client, "5555"))])
    assert response.status_code == 400


def test_an_organisation_is_required(admin_client, uploads):
    response = export(admin_client, None, [chosen("4334")])
    assert response.status_code == 400
    assert "Choose the client organisation" in response.json()["errors"]


def test_very_large_detailed_exports_are_refused(admin_client, uploads, organisation, monkeypatch):
    monkeypatch.setattr(pat_export, "MAX_DETAILED_RESULTS", 1)
    selection = [chosen("4334", "all")]
    assert export(admin_client, organisation, selection, "detailed").status_code == 400
    assert export(admin_client, organisation, selection, "simple").status_code == 200


def test_export_needs_permission_to_see_organisations(client, django_user_model, organisation):
    urls = [reverse("pat_export"), reverse("pat_export_assets")]
    for url in urls:
        assert client.get(url).status_code == 302
    user = django_user_model.objects.create_user(username="someone", password="x")
    client.force_login(user)
    for url in urls:
        assert client.get(url).status_code == 403
    assert export(client, organisation, [chosen("4334")]).status_code == 403
    assert "Export Records" not in client.get(reverse("pat_batch_list")).content.decode()

    user.user_permissions.add(Permission.objects.get(codename="view_organisation"))
    client.force_login(django_user_model.objects.get(pk=user.pk))
    for url in urls:
        assert client.get(url).status_code == 200
    assert "Export Records" in client.get(reverse("pat_batch_list")).content.decode()


def test_upload_choices_say_when_and_by_whom(admin_client, admin_user, uploads):
    first, second = uploads
    models.PATTestBatch.objects.filter(pk=second.pk).update(uploaded_by=None)
    content = admin_client.get(reverse("pat_export")).content.decode()
    assert f"by {admin_user.name.replace(chr(34), '&quot;')}</option>" in content
    assert "theirs.sss · " in content
    assert "by an unknown user</option>" in content


def test_the_page_can_start_with_an_asset_or_upload(admin_client, uploads, pat_asset):
    first, _ = uploads
    response = admin_client.get(reverse("pat_export"), {"asset": "4334", "upload": first.pk})
    content = response.content.decode()
    assert '["4334"]' in content
    assert f'<option value="{first.pk}" selected>' in content
    assert reverse("pat_export") + "?asset=4334" in admin_client.get(pat_asset.get_absolute_url()).content.decode()
