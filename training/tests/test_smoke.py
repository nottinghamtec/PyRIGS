import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "name,kw",
    [
        ("item_list", {}),
        ("item_list_export", {}),
        ("trainee_list", {}),
        ("trainee_detail", {"pk": "trainee"}),
        ("trainee_item_detail", {"pk": "trainee"}),
        ("level_list", {}),
        ("level_detail", {"pk": "level"}),
        ("level_detail", {"pk": "level", "u": "trainee"}),
        ("item_qualification", {"pk": "item"}),
        ("session_log", {}),
    ],
)
def test_training_pages(admin_client, trainee, level, training_item, name, kw):
    objs = {"trainee": trainee, "level": level, "item": training_item}
    kwargs = {k: objs[v].pk for k, v in kw.items()}
    response = admin_client.get(
        reverse(name, kwargs=kwargs), {"item": training_item.pk} if name == "trainee_item_detail" else {}
    )
    assert response.status_code in (200, 302)
