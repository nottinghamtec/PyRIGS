import datetime

import pytest
import reversion
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from RIGS import models
from training.models import TrainingItem, TrainingCategory, TrainingItemQualification

from badges.awarding import award_badges, earned_badges
from badges.models import BadgeAward, BadgeSettings
from badges.stats import ProfileStats


def aware(*args):
    return timezone.make_aware(datetime.datetime(*args))


@pytest.fixture
def member(db):
    return models.Profile.objects.create(
        username="member", first_name="Mem", last_name="Ber", email="member@example.com", is_approved=True
    )


@pytest.fixture
def make_rig(member):
    def make_rig(date, venue=None, status=models.Event.BOOKED, person=None, hours=4, vehicle="", **kwargs):
        event = models.Event.objects.create(name=f"Rig {date}", start_date=date, status=status, venue=venue, **kwargs)
        start = timezone.make_aware(datetime.datetime.combine(date, datetime.time(18)))
        models.EventCheckIn.objects.create(
            event=event,
            person=person or member,
            time=start,
            end_time=start + datetime.timedelta(hours=hours),
            vehicle=vehicle,
        )
        return event

    return make_rig


def earned(profile):
    return earned_badges(ProfileStats(profile))


def test_first_rig_is_dated_to_the_event(member, make_rig):
    make_rig(datetime.date(2024, 3, 1))
    make_rig(datetime.date(2024, 2, 1))
    assert earned(member)["opening-act"] == aware(2024, 2, 1)


def test_cancelled_and_non_rig_events_do_not_count(member, make_rig):
    make_rig(datetime.date(2024, 2, 1), status=models.Event.CANCELLED)
    make_rig(datetime.date(2024, 2, 2), is_rig=False)
    assert "opening-act" not in earned(member)


def test_hours_are_capped_per_check_in(member, make_rig):
    make_rig(datetime.date(2024, 2, 1), hours=200)  # Forgot to check out
    assert ProfileStats(member).total_hours == 24
    assert "clocked-on" not in earned(member)


def test_venues_and_drivers(member, make_rig):
    for i in range(5):
        make_rig(datetime.date(2024, 1, 1 + i), venue=models.Venue.objects.create(name=f"V{i}"), vehicle="Van")
    badges = earned(member)
    assert badges["new-ground"] == aware(2024, 1, 5)
    assert badges["behind-the-wheel"] == aware(2024, 1, 1)


def test_weekend_warrior(member, make_rig):
    # Friday 5th to Sunday 7th January 2024
    for day in (5, 6, 7):
        make_rig(datetime.date(2024, 1, day))
    assert earned(member)["weekend-warrior"] == aware(2024, 1, 7)


def test_weekend_warrior_needs_the_same_weekend(member, make_rig):
    for day in (4, 5, 6):  # Thursday doesn't count
        make_rig(datetime.date(2024, 1, day))
    assert "weekend-warrior" not in earned(member)


def test_night_owl(member, make_rig):
    make_rig(datetime.date(2024, 1, 4), hours=7)  # 18:00 until 01:00
    assert earned(member)["night-owl"] == aware(2024, 1, 5, 1)


def test_mic_without_check_in_counts_as_a_rig(member, make_rig):
    venue = models.Venue.objects.create(name="Old Hall")
    models.Event.objects.create(name="Old Gig", start_date=datetime.date(2009, 6, 26), mic=member, venue=venue)
    models.Event.objects.create(name="Future", start_date=timezone.localdate() + datetime.timedelta(days=5), mic=member)
    mic_and_crew = models.Event.objects.create(name="Both", start_date=datetime.date(2024, 1, 1), mic=member)
    make_rig(datetime.date(2024, 2, 1))
    models.EventCheckIn.objects.create(event=mic_and_crew, person=member, time=aware(2024, 1, 1, 18))

    stats = ProfileStats(member)
    assert [event.name for event in stats.rig_events] == ["Old Gig", "Both", "Rig 2024-02-01"]  # No duplicates
    assert stats.first_rig.venue == venue
    assert earned(member)["opening-act"] == aware(2009, 6, 26)


def test_mic_badges_need_the_event_to_have_happened(member):
    models.Event.objects.create(name="Future", start_date=timezone.localdate() + datetime.timedelta(days=5), mic=member)
    assert "mic-drop" not in earned(member)
    models.Event.objects.create(name="Past", start_date=datetime.date(2024, 1, 1), mic=member)
    assert earned(member)["mic-drop"] == aware(2024, 1, 1)


def test_teaching_and_training(member, admin_user):
    category = TrainingCategory.objects.create(reference_number=1, name="Basics")
    item = TrainingItem.objects.create(category=category, reference_number=1, description="Thing")
    TrainingItemQualification.objects.create(
        item=item, trainee=member, supervisor=admin_user, depth=TrainingItemQualification.PASSED_OUT, date="2024-01-01"
    )
    assert earned(member)["passed-out"] == aware(2024, 1, 1)
    assert earned(admin_user)["passing-it-on"] == aware(2024, 1, 1)


RA_ANSWERS = dict.fromkeys(
    [
        "nonstandard_equipment",
        "nonstandard_use",
        "contractors",
        "other_companies",
        "crew_fatigue",
        "big_power",
        "generators",
        "other_companies_power",
        "nonstandard_equipment_power",
        "multiple_electrical_environments",
        "noise_monitoring",
        "known_venue",
        "safe_loading",
        "safe_storage",
        "area_outside_of_control",
        "barrier_required",
        "nonstandard_emergency_procedure",
        "special_structures",
        "suspended_structures",
        "outside",
        "parking_and_access",
    ],
    False,
)


def test_risk_assessment_badge_goes_to_the_author_not_the_reviewer(member, admin_user):
    event = models.Event.objects.create(name="RA Event", start_date=datetime.date(2024, 1, 1))
    with reversion.create_revision():
        reversion.set_user(member)
        ra = models.RiskAssessment.objects.create(event=event, **RA_ANSWERS)
    with reversion.create_revision():
        reversion.set_user(admin_user)
        ra.reviewed_by = admin_user
        ra.save()
    assert "risk-aware" in earned(member)
    assert "risk-aware" not in earned(admin_user)


def test_award_badges_dry_run_and_idempotence(member, make_rig):
    rig_date = timezone.localdate() - datetime.timedelta(days=10)  # Too recent for an anniversary
    make_rig(rig_date)
    profiles = models.Profile.objects.filter(pk=member.pk)

    assert [badge.slug for _, badge, *_ in award_badges(profiles, dry_run=True)] == ["opening-act"]
    assert not BadgeAward.objects.exists()

    assert len(award_badges(profiles)) == 1
    assert timezone.localtime(BadgeAward.objects.get().awarded_at).date() == rig_date
    assert award_badges(profiles) == []

    # Awards are never taken away, unless reset
    models.Event.objects.update(status=models.Event.CANCELLED)
    assert award_badges(profiles) == []
    assert BadgeAward.objects.count() == 1
    award_badges(profiles, reset=True)
    assert not BadgeAward.objects.exists()


def test_command(member, make_rig, capsys):
    make_rig(datetime.date(2024, 2, 1))
    call_command("award_badges", "--dry-run", "--user", "member")
    out = capsys.readouterr().out
    assert "Would award Opening Act" in out
    assert "Badges are not live" in out
    assert not BadgeAward.objects.exists()


@pytest.fixture
def member_client(client, member):
    client.force_login(member)
    return client


def set_live(badges=False, tech_rider=False, **superusers):
    settings = BadgeSettings.load()
    settings.badges_live = badges
    settings.tech_rider_live = tech_rider
    settings.badges_superusers = superusers.get("badges_superusers", False)
    settings.tech_rider_superusers = superusers.get("tech_rider_superusers", False)
    settings.save()


def test_badges_hidden_until_live(member_client, admin_client):
    url = reverse("badge_list")
    assert member_client.get(url).status_code == 404
    assert admin_client.get(url).status_code == 404  # Superusers don't get in automatically...
    set_live(badges_superusers=True)
    response = admin_client.get(url)  # ...only if the settings allow it
    assert response.status_code == 200
    assert b"aren&#x27;t live yet" in response.content or b"aren't live yet" in response.content
    assert member_client.get(url).status_code == 404
    set_live(badges=True)
    assert member_client.get(url).status_code == 200


def test_badge_shelf_on_profile(member, member_client, make_rig):
    make_rig(datetime.date(2024, 2, 1))
    award_badges()
    url = reverse("profile_detail")
    assert b"Opening Act" not in member_client.get(url).content
    set_live(badges=True)
    assert b"Opening Act" in member_client.get(url).content


def test_tech_rider_gating(member, member_client, admin_client, admin_user, make_rig):
    make_rig(datetime.date(2024, 2, 1), venue=models.Venue.objects.create(name="The Hall"))
    own, other = reverse("tech_rider"), reverse("tech_rider", kwargs={"pk": admin_user.pk})

    assert member_client.get(own).status_code == 404
    members_rider = reverse("tech_rider", kwargs={"pk": member.pk})
    assert admin_client.get(members_rider).status_code == 404
    set_live(tech_rider_superusers=True)
    response = admin_client.get(members_rider)
    assert response.status_code == 200
    assert b"The Hall" in response.content
    assert member_client.get(own).status_code == 404

    set_live(tech_rider=True)
    assert member_client.get(own).status_code == 200
    assert member_client.get(other).status_code == 404  # Only superusers can see other people's


@pytest.fixture
def recent_rig(member, make_rig):
    return make_rig(timezone.localdate() - datetime.timedelta(days=2))


def awards_by_slug():
    return {award.slug: award for award in BadgeAward.objects.all()}


def test_nothing_emailed_while_not_live(member, recent_rig, mailoutbox):
    call_command("award_badges", "--quiet")
    assert awards_by_slug()["opening-act"].email == BadgeAward.EMAIL_SKIPPED
    assert mailoutbox == []


def test_only_recent_badges_are_emailed(member, make_rig, recent_rig, mailoutbox):
    make_rig(timezone.localdate() - datetime.timedelta(days=60))  # Opening Act, but too long ago to email about
    recent_rig.mic = member
    recent_rig.save()  # Mic Drop, just now
    set_live(badges=True)
    call_command("award_badges", "--quiet")

    awards = awards_by_slug()
    assert awards["opening-act"].email == BadgeAward.EMAIL_SKIPPED
    assert awards["mic-drop"].email == BadgeAward.EMAIL_SENT
    assert awards["mic-drop"].emailed_at is not None
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [member.email]
    assert mailoutbox[0].subject == "You've earned a badge: Mic Drop"
    assert "Opening Act" not in mailoutbox[0].body

    call_command("award_badges", "--quiet")
    assert len(mailoutbox) == 1  # Nothing new, nothing sent


def test_digest_lists_every_new_badge(member, recent_rig, mailoutbox):
    models.Event.objects.update(mic=member)  # Same rig earns Mic Drop too
    set_live(badges=True)
    call_command("award_badges", "--quiet")
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "You've earned 2 new badges"
    assert "Mic Drop" in mailoutbox[0].body and "Opening Act" in mailoutbox[0].body
    assert "&#x27;" not in mailoutbox[0].body


def test_opted_out_members_are_not_emailed(member, recent_rig, mailoutbox):
    member.badge_emails = False
    member.save()
    set_live(badges=True)
    call_command("award_badges", "--quiet")
    assert awards_by_slug()["opening-act"].email == BadgeAward.EMAIL_OPTED_OUT
    assert mailoutbox == []


def test_reset_never_emails(member, recent_rig, mailoutbox):
    set_live(badges=True)
    call_command("award_badges", "--quiet", "--no-email")
    call_command("award_badges", "--quiet", "--reset")
    assert awards_by_slug()["opening-act"].email == BadgeAward.EMAIL_SKIPPED
    assert mailoutbox == []


def test_dry_run_previews_going_live(member, recent_rig, mailoutbox, capsys):
    call_command("award_badges", "--dry-run", "--as-if-live")
    out = capsys.readouterr().out
    assert "1 queued for email" in out
    assert f"Email to {member} (would send): Opening Act" in out
    assert not BadgeAward.objects.exists()
    assert mailoutbox == []


# --- Badges added in the second batch ---


def test_clients(member):
    org = models.Organisation.objects.create(name="Drama Soc")
    for day in range(1, 6):
        models.Event.objects.create(
            name=f"Show {day}", start_date=datetime.date(2024, 1, day), mic=member, organisation=org
        )
    badges = earned(member)
    assert badges["regular-customer"] == aware(2024, 1, 5)
    assert "networker" not in badges

    for n in range(9):
        person = models.Person.objects.create(name=f"Client {n}")
        models.Event.objects.create(
            name=f"Gig {n}", start_date=datetime.date(2024, 2, 1 + n), mic=member, person=person
        )
    assert earned(member)["networker"] == aware(2024, 2, 9)  # Drama Soc plus nine people


def test_signed_sealed_delivered(member, admin_user):
    event = models.Event.objects.create(name="Authorised", start_date=datetime.date(2024, 3, 1), mic=member)
    assert "signed-sealed-delivered" not in earned(member)
    models.EventAuthorisation.objects.create(
        event=event, email="c@example.com", name="C", amount=10, sent_by=admin_user
    )
    assert earned(member)["signed-sealed-delivered"] == aware(2024, 3, 1)


def test_admin_badges_come_from_version_history(member):
    with reversion.create_revision():
        reversion.set_user(member)
        models.Venue.objects.create(name="New Place")
    stats = ProfileStats(member)
    assert "venue-scout" in earned_badges(stats)
    assert len(stats.revisions) == 1


def test_store_badges_count_changes_not_audits(member):
    from assets.models import Asset, AssetCategory, AssetStatus

    category = AssetCategory.objects.create(name="Cables")
    status = AssetStatus.objects.create(name="Working", should_show=True)
    with reversion.create_revision():
        reversion.set_user(member)
        cable = Asset.objects.create(
            asset_id="C1",
            description="XLR",
            category=category,
            status=status,
            date_acquired=datetime.date(2024, 1, 1),
            is_cable=True,
        )
    for n in range(3):
        with reversion.create_revision():
            reversion.set_user(member)
            cable.comments = f"Edit {n}"
            cable.save()
    stats = ProfileStats(member)
    assert len(stats.asset_edits) == 4  # Creating it counts as a change too
    assert len(stats.cable_edits) == 4
    assert stats.authored(Asset) and "asset-wrangler" not in earned_badges(stats)


def test_departments(member):
    from training.models import TrainingLevel, TrainingLevelQualification

    dates = {}
    for n, department in enumerate(
        (TrainingLevel.SOUND, TrainingLevel.LIGHTING, TrainingLevel.POWER, TrainingLevel.RIGGING)
    ):
        level = TrainingLevel.objects.create(department=department, level=TrainingLevel.TECHNICIAN)
        dates[department] = aware(2024, 1, 1 + n)
        TrainingLevelQualification.objects.create(trainee_id=member.pk, level=level, confirmed_on=dates[department])
    badges = earned(member)
    assert badges["sound-technician"] == dates[TrainingLevel.SOUND]
    assert badges["full-house"] == dates[TrainingLevel.RIGGING]


def test_crew_counts_check_ins_and_the_mic(member, make_rig, admin_user):
    other = models.Profile.objects.create(username="other", email="other@example.com")
    first = make_rig(datetime.date(2024, 1, 1))
    models.EventCheckIn.objects.create(event=first, person=other, time=aware(2024, 1, 1, 18))
    make_rig(datetime.date(2024, 1, 8), mic=other)  # Other didn't check in, but was MIC
    make_rig(datetime.date(2024, 1, 15), mic=admin_user)

    stats = ProfileStats(member)
    assert stats.crewmates == [(other, 2), (admin_user, 1)]
    assert stats.crewmates_reached(shared=2) == datetime.date(2024, 1, 8)
    assert stats.crewmates_reached(distinct=2) == datetime.date(2024, 1, 15)


def test_seasons(member, make_rig):
    make_rig(datetime.date(2023, 10, 30), end_date=datetime.date(2023, 11, 1))  # Spans Halloween, and 3 days long
    make_rig(datetime.date(2025, 7, 10))  # Summer, and more than a year since the last
    badges = earned(member)
    assert badges["fright-night"] == aware(2023, 10, 31)
    assert badges["marathon"] == aware(2023, 11, 1)
    assert badges["summer-season"] == aware(2025, 7, 10)
    assert badges["comeback-tour"] == aware(2025, 7, 10)


def test_inactive_accounts_do_not_earn_badges(member, make_rig):
    make_rig(datetime.date(2024, 2, 1))
    award_badges()
    member.is_active = False
    member.save()
    make_rig(datetime.date(2024, 2, 2), mic=member)

    assert award_badges() == []  # No Mic Drop
    assert BadgeAward.objects.filter(profile=member).count() > 0  # Existing awards stay...
    award_badges(reset=True)
    assert not BadgeAward.objects.filter(profile=member).exists()  # ...unless reset


def test_common_competencies_are_not_a_level(member):
    from training.models import TrainingLevel, TrainingLevelQualification

    def confirm(level, **kwargs):
        TrainingLevelQualification.objects.create(
            trainee_id=member.pk,
            level=TrainingLevel.objects.create(level=level, **kwargs),
            confirmed_on=aware(2024, 1, 1),
        )

    confirm(TrainingLevel.TECHNICIAN)  # Technician Common Competencies
    confirm(TrainingLevel.SUPERVISOR)  # Supervisor Common Competencies
    confirm(TrainingLevel.SUPERVISOR, department=TrainingLevel.HAULAGE)
    badges = earned(member)
    assert "supervisor" not in badges
    assert badges["technician"] == aware(2024, 1, 1)  # From the Haulage level, which is a real department

    confirm(TrainingLevel.SUPERVISOR, department=TrainingLevel.SOUND)
    assert "supervisor" in earned(member)


def grant(profile, codename):
    from django.contrib.auth.models import Permission

    profile.user_permissions.add(Permission.objects.get(content_type__app_label="badges", codename=codename))


def test_view_badges_permission_previews_badges(member, member_client):
    url = reverse("badge_list")
    assert member_client.get(url).status_code == 404
    grant(member, "view_badges")
    response = member_client.get(url)
    assert response.status_code == 200
    assert reverse("admin:badges_badgesettings_changelist").encode() not in response.content  # Superusers only
    assert member_client.get(reverse("tech_rider")).status_code == 404  # Separate permission


def test_view_tech_rider_permission_is_for_your_own(member, member_client, admin_user):
    grant(member, "view_tech_rider")
    assert member_client.get(reverse("tech_rider")).status_code == 200
    assert member_client.get(reverse("tech_rider", kwargs={"pk": admin_user.pk})).status_code == 404


def test_single_page_authorship_matches_the_shared_history(member, admin_user):
    from badges.stats import build_history

    for n, author in enumerate([member, member, admin_user]):
        event = models.Event.objects.create(name=f"RA {n}", start_date=datetime.date(2024, 1, 1 + n))
        with reversion.create_revision():
            reversion.set_user(author)
            ra = models.RiskAssessment.objects.create(event=event, **RA_ANSWERS)
        with reversion.create_revision():  # Edited by someone else afterwards
            reversion.set_user(admin_user if author == member else member)
            ra.save()

    history = build_history()
    for profile in (member, admin_user):
        assert ProfileStats(profile).authored() == ProfileStats(profile, history).authored()
    assert len(ProfileStats(member).authored(models.RiskAssessment)) == 2


def test_permissions_still_work_for_superusers(admin_user, admin_client):
    # Superusers pass every has_perm() check, so make sure it's an actual grant that counts
    assert admin_client.get(reverse("badge_list")).status_code == 404
    grant(admin_user, "view_badges")
    assert admin_client.get(reverse("badge_list")).status_code == 200
    assert admin_client.get(reverse("tech_rider")).status_code == 404


def test_permissions_can_come_from_a_group(member, member_client):
    from django.contrib.auth.models import Group, Permission

    group = Group.objects.create(name="Badge testers")
    group.permissions.add(Permission.objects.get(content_type__app_label="badges", codename="view_tech_rider"))
    member.groups.add(group)
    assert member_client.get(reverse("tech_rider")).status_code == 200
