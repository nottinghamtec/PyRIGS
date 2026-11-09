import json

import pytest
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import reverse

from PyRIGS.commands import COMMANDS, commands_for
from RIGS import models


@pytest.fixture
def basic_user(db):
    return models.Profile.objects.create(
        username="basic", first_name="Basic", last_name="User", initials="BU", is_approved=True
    )


def titles_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return {command["title"] for command in commands_for(request)}


def palette(response):
    content = response.content.decode()
    start = content.index('<script id="command-palette-data" type="application/json">') + len(
        '<script id="command-palette-data" type="application/json">'
    )
    return json.loads(content[start : content.index("</script>", start)])


def test_basic_users_only_see_what_they_can_open(basic_user):
    titles = titles_for(basic_user)
    assert {"Rigboard", "Asset List", "My Training Record", "Notifications", "Log Out"} <= titles
    assert not titles & {"New Event", "Invoice Dashboard", "People", "Audit Assets", "Django Admin", "Check-in Report"}


def test_permissions_unlock_commands(basic_user):
    basic_user.user_permissions.add(
        Permission.objects.get(codename="add_event"), Permission.objects.get(codename="view_invoice")
    )
    basic_user = models.Profile.objects.get(pk=basic_user.pk)
    titles = titles_for(basic_user)
    assert {"New Event", "New Enquiry", "Invoice Dashboard", "Outstanding Invoices"} <= titles
    assert "Invoices Waiting" not in titles


def test_superusers_see_every_command_and_every_one_opens(admin_client, admin_user):
    request = RequestFactory().get("/")
    request.user = admin_user
    commands = commands_for(request)
    assert {command["title"] for command in commands} >= {
        command.title
        for command in COMMANDS
        if command.title not in {"Check Out", "Badges", "Badge Leaderboard", "Tech Rider"}
    }
    for command in commands:
        if command["method"] == "get":
            response = admin_client.get(command["url"])
            assert response.status_code in (200, 302), (command["title"], response.status_code)


def test_palette_is_rendered_for_signed_in_users_only(client, basic_user):
    response = client.get(reverse("login"))
    assert b"command-palette-data" not in response.content

    client.force_login(basic_user)
    response = client.get(reverse("index"))
    data = palette(response)
    assert "Rigboard" in {command["title"] for command in data}
    assert "New Event" not in {command["title"] for command in data}
    assert b'id="command-palette"' in response.content


def test_log_out_command_posts(admin_client):
    response = admin_client.get(reverse("index"))
    log_out = next(command for command in palette(response) if command["title"] == "Log Out")
    assert log_out["method"] == "post"
    admin_client.post(log_out["url"])
    assert "_auth_user_id" not in admin_client.session


MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Safari/605.1.15"
)
IPAD = "Mozilla/5.0 (iPad; CPU OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
WINDOWS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0"


@pytest.mark.parametrize(
    "user_agent, keys, label",
    [
        (MAC, "<kbd>⌘</kbd> <kbd>K</kbd>", "⌘K"),
        (IPAD, "<kbd>⌘</kbd> <kbd>K</kbd>", "⌘K"),
        (WINDOWS, "<kbd>Ctrl</kbd> <kbd>K</kbd>", "Ctrl K"),
        (LINUX, "<kbd>Ctrl</kbd> <kbd>K</kbd>", "Ctrl K"),
        ("", "<kbd>Ctrl</kbd> <kbd>K</kbd>", "Ctrl K"),
    ],
)
def test_shortcuts_match_the_viewers_device(admin_client, user_agent, keys, label):
    response = admin_client.get(reverse("index"), HTTP_USER_AGENT=user_agent)
    content = response.content.decode()
    assert f"Press {keys} on any page" in content
    assert f'<kbd class="command-palette-shortcut">{label}</kbd>' in content
    assert f'data-shortcut="{label}"' in content
    other = "Ctrl" if "⌘" in label else "⌘"
    assert f"<kbd>{other}</kbd>" not in content


@pytest.mark.parametrize("user_agent, alt", [(MAC, "⌥"), (WINDOWS, "Alt")])
def test_quick_jump_keys_match_the_viewers_device(admin_client, user_agent, alt):
    content = admin_client.get(reverse("index"), HTTP_USER_AGENT=user_agent).content.decode()
    assert f'data-alt="{alt}"' in content
    assert f"<kbd>{alt}</kbd> <kbd>1</kbd>–<kbd>9</kbd> jump" in content
    assert f"press <kbd>{alt}</kbd> and a number" in content


def test_pat_commands_follow_permissions(basic_user):
    titles = titles_for(basic_user)
    assert {"PAT Uploads", "Assets Needing PAT"} <= titles
    assert "Upload PAT Results" not in titles
    basic_user.user_permissions.add(Permission.objects.get(codename="add_pattestbatch"))
    assert "Upload PAT Results" in titles_for(models.Profile.objects.get(pk=basic_user.pk))


def test_assets_needing_pat_opens_the_filtered_list(admin_client, admin_user):
    request = RequestFactory().get("/")
    request.user = admin_user
    command = next(command for command in commands_for(request) if command["title"] == "Assets Needing PAT")
    assert command["url"] == f"{reverse('asset_list')}?pat_status=needs"
    response = admin_client.get(command["url"])
    assert response.status_code == 200
    assert response.context["form"].cleaned_data["pat_status"] == "needs"


def test_commands_without_a_query_have_plain_urls(admin_user):
    request = RequestFactory().get("/")
    request.user = admin_user
    urls = {command["title"]: command["url"] for command in commands_for(request)}
    assert urls["PAT Uploads"] == reverse("pat_batch_list")
    assert "?" not in urls["Asset List"]


def test_the_home_page_only_offers_the_pat_upload_button(admin_client, client, basic_user):
    content = admin_client.get(reverse("index")).content.decode()
    assert f'href="{reverse("pat_upload")}"' in content
    assert f'href="{reverse("pat_batch_list")}"' not in content
    assert f'href="{reverse("asset_list")}?pat_status=needs"' not in content
    assert "Assets Needing PAT" in {command["title"] for command in palette(admin_client.get(reverse("index")))}
    client.force_login(basic_user)
    content = client.get(reverse("index")).content.decode()
    assert "You need permission to upload PAT results" in content
    assert f'href="{reverse("pat_upload")}"' not in content
