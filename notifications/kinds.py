from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class Kind:
    slug: str
    label: str
    description: str
    default_push: bool = True
    default_email: bool = False
    email_configurable: bool = True
    audience: str = ""


KINDS_LIST = [
    Kind(
        "rig_changed",
        "A rig I'm MIC on changes",
        "It's cancelled, or its date, venue, meet time or access time changes.",
        default_email=True,
    ),
    Kind("mic_assigned", "I'm made (or stop being) MIC", "You're assigned to, or taken off, a rig as MIC."),
    Kind("meet_reminder", "Meet time is coming up", "Two hours before the meet time of a rig you're MIC on."),
    Kind(
        "not_checked_in",
        "I haven't checked in",
        "Shortly after the meet time of a rig you're MIC on, if you haven't checked in.",
    ),
    Kind(
        "ra_reminder",
        "Risk assessment overdue",
        "A rig is close and its risk assessment isn't done.",
        default_email=True,
    ),
    Kind(
        "checkout_nag",
        "I'm still checked in",
        "You've been checked in to a rig for a long time.",
        default_email=True,
    ),
    Kind(
        "review_complete",
        "My H&S paperwork is approved",
        "Your risk assessment, checklist or power test was reviewed and approved.",
    ),
    Kind("auth_pending", "An authorisation request is unanswered", "A request you sent hasn't been completed."),
    Kind(
        "auth_completed",
        "A client authorises a rig",
        "A client completes an authorisation you requested, or for a rig you're MIC on.",
        default_email=True,
    ),
    Kind("auth_bounced", "An authorisation email fails", "We couldn't deliver an authorisation email you sent."),
    Kind(
        "invoice_waiting", "A rig is waiting to be invoiced", "A finished rig has no invoice yet.", audience="finance"
    ),
    Kind("training_logged", "Training is logged for me", "A trainer records a qualification for you."),
    Kind(
        "level_ready",
        "Someone meets a level's requirements",
        "You (or someone you trained) can now be confirmed in a level.",
    ),
    Kind("pat_batch_complete", "A PAT upload finishes", "Results have been imported.", audience="pat"),
    Kind(
        "admin_approval",
        "Users are awaiting approval",
        "New accounts need approving.",
        default_email=True,
        audience="admin",
    ),
    Kind("badge_earned", "I earn a badge", "You earn a new badge.", default_email=True),
]

KINDS = {kind.slug: kind for kind in KINDS_LIST}


def visible_to(kind, user):
    if kind.audience == "finance":
        return user.groups.filter(name=settings.NOTIFICATION_FINANCE_GROUP).exists()
    if kind.audience == "pat":
        return user.groups.filter(name=settings.NOTIFICATION_PAT_GROUP).exists()
    if kind.audience == "admin":
        return any(user.email == address for _, address in settings.ADMINS)
    return True
