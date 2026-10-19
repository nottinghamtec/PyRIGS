import datetime
import re

import pytest
from django.template import Context, Template, TemplateSyntaxError, engines
from django.template.loader import get_template
from django.urls import reverse
from django.utils.html import escape
from pytest_django.asserts import assertContains, assertNotContains

from RIGS.templatetags import changelog


def render(source, **context):
    return Template("{% load changelog %}" + source).render(Context(context))


def test_entry_uses_author_profile(admin_user):
    html = render(
        '{% changelog_entry author=username date="2026-10-19" title="A change" %}<p>{{ 1|add:1 }} things</p>{% endchangelog_entry %}',
        username=admin_user.username,
    )
    assert escape(admin_user.name) in html
    assert escape(admin_user.profile_picture) in html
    assert reverse("profile_detail", kwargs={"pk": admin_user.pk}) in html
    assert 'datetime="2026-10-19"' in html
    assert "A change" in html
    assert "<p>2 things</p>" in html


def test_entry_unknown_author_falls_back():
    html = render('{% changelog_entry author="nobody" date="2026-10-19" %}Hi{% endchangelog_entry %}')
    assert "nobody" in html
    assert "pyrigs-avatar" in html


@pytest.mark.parametrize(
    "tag",
    [
        '{% changelog_entry date="2026-10-19" %}{% endchangelog_entry %}',
        '{% changelog_entry author="a" %}{% endchangelog_entry %}',
        '{% changelog_entry author="a" date="2026-10-19" colour="red" %}{% endchangelog_entry %}',
        '{% changelog_entry "a" date="2026-10-19" %}{% endchangelog_entry %}',
    ],
)
def test_entry_rejects_bad_arguments(tag):
    with pytest.raises(TemplateSyntaxError):
        render(tag)


def test_entries_sorted_newest_first(tmp_path, monkeypatch):
    for name in ["2026-01-02-b.html", "2025-12-31-a.html", "2026-03-01-c.html", "_draft.html", "notes.txt"]:
        (tmp_path / name).touch()
    monkeypatch.setattr(changelog, "ENTRIES_DIR", tmp_path)
    assert changelog.entry_template_names() == [
        "changelog/entries/2026-03-01-c.html",
        "changelog/entries/2026-01-02-b.html",
        "changelog/entries/2025-12-31-a.html",
    ]


def test_real_entries_are_valid():
    """Every committed entry must compile, and filename order must agree with the dates inside."""
    dates = []
    for name in changelog.entry_template_names():
        source = (changelog.ENTRIES_DIR / name.rsplit("/", 1)[1]).read_text()
        get_template(name)
        match = re.search(r'date="(\d{4}-\d{2}-\d{2})"', source)
        assert match, f"{name} has no date"
        dates.append(datetime.date.fromisoformat(match.group(1)))
    assert dates == sorted(dates, reverse=True)


def test_index_shows_changelog(admin_client):
    response = admin_client.get(reverse("index"))
    assertContains(response, "What's New")
    assertContains(response, "changelog-entry")


@pytest.fixture
def fake_entries(tmp_path, monkeypatch):
    """Twelve visible entries (entry 0 oldest, entry 11 newest) and one that hides itself."""
    from django.template.loader import get_template as real_get_template

    sources = {}
    for i in range(12):
        sources[f"2026-01-{i + 1:02}.html"] = (
            "{% load changelog %}{% changelog_entry author=user.username date='2026-01-01' %}"
            f"entry {i}.{{% endchangelog_entry %}}"
        )
    sources["2026-02-01.html"] = "{% if False %}hidden{% endif %}"
    for name in sources:
        (tmp_path / name).touch()
    monkeypatch.setattr(changelog, "ENTRIES_DIR", tmp_path)
    monkeypatch.setattr(
        changelog,
        "get_template",
        lambda name: (
            engines["django"].from_string(sources[name.rsplit("/", 1)[1]])
            if name.startswith("changelog/entries/")
            else real_get_template(name)
        ),
    )


def test_hidden_entries_are_skipped_and_paginated(fake_entries, rf, admin_user):
    request = rf.get("/")
    request.user = admin_user
    page = changelog.changelog_page(request)["page_obj"]
    assert page.paginator.count == 12
    assert page.paginator.num_pages == 3
    assert "entry 11." in page.object_list[0]
    assert not any("hidden" in entry for entry in page.paginator.object_list)


def test_changelog_page_ajax_returns_fragment(fake_entries, admin_client):
    response = admin_client.get(reverse("changelog"), {"page": 2}, headers={"x-requested-with": "XMLHttpRequest"})
    assertContains(response, "entry 6.")
    assertContains(response, "entry 2.")
    assertNotContains(response, "entry 7.")
    assertNotContains(response, "entry 1.")
    assertNotContains(response, "card-header")
    assertContains(response, f'href="{reverse("changelog")}?page=3"')


def test_changelog_page_full(fake_entries, admin_client):
    response = admin_client.get(reverse("changelog"), {"page": "nonsense"})
    assertContains(response, "card-header")
    assertContains(response, "entry 11.")
    assertNotContains(response, "entry 6.")


@pytest.mark.parametrize("days_old, is_new", [(0, True), (6, True), (7, False), (30, False)])
def test_new_pill(days_old, is_new):
    from django.utils import timezone

    date = (timezone.localdate() - datetime.timedelta(days=days_old)).isoformat()
    html = render(f'{{% changelog_entry author="nobody" date="{date}" %}}Hi{{% endchangelog_entry %}}')
    assert ("changelog-new" in html) == is_new
