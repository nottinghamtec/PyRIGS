import re

from django.db import migrations

TRAILING_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿]️?$")
MAX_LENGTH = 5


def normalise(value):
    if not value:
        return value
    value = value.strip()
    emoji = TRAILING_EMOJI.search(value)
    if emoji:
        value = value[: emoji.start()]
    value = "".join(c for c in value.upper() if c.isalnum())
    return value + (emoji.group(0) if emoji else "")


def candidates(initials, first_name):
    letters = [c.upper() for c in first_name.strip()[1:] if c.isalpha()]
    for letter in letters:
        yield (initials[:1] + letter + initials[1:])[:MAX_LENGTH]
    for digit in range(2, 10):
        yield (initials[: MAX_LENGTH - 1] + str(digit))[:MAX_LENGTH]


def normalise_initials(apps, schema_editor):
    Profile = apps.get_model("RIGS", "Profile")
    profiles = list(Profile.objects.exclude(initials__isnull=True).order_by("date_joined", "pk"))
    normalised = {p.pk: normalise(p.initials) for p in profiles}

    taken = set()
    for p in profiles:
        if p.is_active and normalised[p.pk]:
            taken.add(normalised[p.pk].upper())

    claimed = set()
    for p in profiles:
        value = normalised[p.pk]
        if p.is_active and value:
            if value.upper() in claimed:
                for candidate in candidates(value, p.first_name):
                    if candidate.upper() not in taken:
                        value = candidate
                        break
                taken.add(value.upper())
            claimed.add(value.upper())
        if value != p.initials:
            Profile.objects.filter(pk=p.pk).update(initials=value)


class Migration(migrations.Migration):
    dependencies = [
        ("RIGS", "0057_profile_badge_emails"),
    ]

    operations = [
        migrations.RunPython(normalise_initials, migrations.RunPython.noop),
    ]
