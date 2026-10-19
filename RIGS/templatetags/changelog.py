"""
Front page changelog.

Each entry is its own template in ``templates/changelog/entries/``, wrapped in a
``{% changelog_entry %}`` block that carries its metadata::

    {% load changelog %}
    {% changelog_entry author="username" date="2026-10-19" title="Something new" %}
        <p>Any Django templating, e.g. {% url 'rigboard' %} or {% include 'changelog/fragments/...' %}</p>
    {% endchangelog_entry %}

Wrap the whole entry in an ``{% if %}`` to show it only to some users; entries that
render nothing are skipped. They are paginated on the front page and at ``/changelog/``,
newest first by sorting their filenames lexicographically, so name
them ``YYYY-MM-DD-short-slug.html``.
"""

import datetime

from django import template
from django.conf import settings
from django.core.paginator import Paginator
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from RIGS.models import Profile

register = template.Library()

ENTRIES_DIR = settings.BASE_DIR / "templates" / "changelog" / "entries"


def entry_template_names():
    """All changelog entry templates, newest (lexicographically last) first."""
    if not ENTRIES_DIR.is_dir():
        return []
    files = sorted(
        (f.name for f in ENTRIES_DIR.iterdir() if f.suffix == ".html" and not f.name.startswith("_")), reverse=True
    )
    return [f"changelog/entries/{name}" for name in files]


PER_PAGE = 5
# Entries younger than this get a "New" pill
NEW_FOR_DAYS = 7


def visible_entries(request):
    """Render every entry for this request, dropping any that hide themselves by rendering nothing."""
    # Shared across entries so each author is only looked up once
    context = {"changelog_authors": {}}
    entries = []
    for name in entry_template_names():
        html = get_template(name).render(context, request)
        if html.strip():
            entries.append(html)
    return entries


def changelog_page(request, number=1):
    """The context for one page of the changelog, as used by ``changelog/page.html``."""
    paginator = Paginator(visible_entries(request), PER_PAGE)
    page = paginator.get_page(number)
    return {
        "page_obj": page,
        "page_range": paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1),
        "ellipsis": paginator.ELLIPSIS,
    }


@register.inclusion_tag("changelog/changelog.html", takes_context=True)
def changelog(context):
    return changelog_page(context["request"])


class ChangelogEntryNode(template.Node):
    def __init__(self, nodelist, kwargs):
        self.nodelist = nodelist
        self.kwargs = kwargs

    def render(self, context):
        values = {key: value.resolve(context) for key, value in self.kwargs.items()}
        username = values.get("author")
        date = datetime.date.fromisoformat(values["date"])
        authors = context.get("changelog_authors", {})
        if username not in authors:
            authors[username] = Profile.objects.filter(username=username).first()
        return render_to_string(
            "changelog/entry.html",
            {
                "author": authors[username],
                "username": username,
                "date": date,
                "is_new": (timezone.localdate() - date).days < NEW_FOR_DAYS,
                "title": values.get("title"),
                "body": self.nodelist.render(context),
            },
        )


@register.tag
def changelog_entry(parser, token):
    bits = token.split_contents()
    tag_name = bits[0]
    kwargs = template.base.token_kwargs(bits[1:], parser)
    if len(kwargs) != len(bits) - 1:
        raise template.TemplateSyntaxError(f"'{tag_name}' only takes keyword arguments")
    missing = {"author", "date"} - kwargs.keys()
    if missing:
        raise template.TemplateSyntaxError(f"'{tag_name}' requires {', '.join(sorted(missing))}")
    unknown = kwargs.keys() - {"author", "date", "title"}
    if unknown:
        raise template.TemplateSyntaxError(f"'{tag_name}' got unexpected arguments {', '.join(sorted(unknown))}")
    nodelist = parser.parse((f"end{tag_name}",))
    parser.delete_first_token()
    return ChangelogEntryNode(nodelist, kwargs)
