# Front page changelog

Each file in `entries/` is one changelog entry, shown newest first by sorting
filenames lexicographically, so name them `YYYY-MM-DD-short-slug.html`.
Files starting with `_` are ignored.

```django
{% load changelog %}
{% changelog_entry author="username" date="2026-10-19" title="Something new" %}
    <p>Any Django templating works here: {% url 'rigboard' %}, filters, and
    reusable snippets via {% include 'changelog/fragments/example.html' %}.</p>
{% endchangelog_entry %}
```

- `author` is a RIGS username; their name and profile picture are looked up
  from their profile. An unknown username falls back to the default avatar.
- `date` is an ISO date (`YYYY-MM-DD`).
- `title` is optional.

To show an entry only to some users, wrap the whole thing in an `{% if %}`
(e.g. `{% if perms.RIGS.view_invoice %}`). Entries that render nothing are
skipped, so they don't count towards the five shown before "Show older".

When several entries share a date, add a number after it
(`2026-10-19-1-…`, `2026-10-19-2-…`); the highest number shows first.

Shared snippets for entries can live in `fragments/`.
