from dataclasses import dataclass
from typing import Callable

from django.urls import reverse


@dataclass
class Command:
    title: str
    section: str
    url_name: str
    icon: str
    permission: str | None = None
    check: Callable | None = None
    keywords: str = ""
    method: str = "get"
    url_kwargs: Callable | None = None

    def allowed(self, request):
        user = request.user
        if self.permission and not user.has_perm(self.permission):
            return False
        return self.check is None or self.check(request)

    def as_dict(self, request):
        kwargs = self.url_kwargs(request) if self.url_kwargs else {}
        return {
            "title": self.title,
            "section": self.section,
            "url": reverse(self.url_name, kwargs=kwargs),
            "icon": self.icon,
            "keywords": self.keywords,
            "method": self.method,
        }


def _superuser(request):
    return request.user.is_superuser


def _staff(request):
    return request.user.is_staff


def _can_log_training(request):
    from training.models import Trainee

    if request.user.is_supervisor:
        return True
    trainee = Trainee.objects.filter(pk=request.user.pk).first()
    return trainee is not None and trainee.can_log_training


def _checked_in(request):
    return request.user.current_event() is not None


def _badges_visible(request):
    from badges import views
    from badges.templatetags.badge_tags import request_settings

    return views.badges_visible(request.user, request_settings(request))


def _tech_rider_visible(request):
    from badges import views
    from badges.templatetags.badge_tags import request_settings

    return views.tech_rider_visible(request.user, request_settings(request))


RIGBOARD = "Rigboard"
CREATE = "Create"
FINANCE = "Finance"
CONTACTS = "Contacts"
ASSETS = "Assets"
TRAINING = "Training"
ACCOUNT = "You"
HELP = "Help"

COMMANDS = [
    Command("Home", RIGBOARD, "index", "fa-home", keywords="dashboard start"),
    Command("Rigboard", RIGBOARD, "rigboard", "fa-list", keywords="events upcoming rigs"),
    Command("Kanban", RIGBOARD, "event_kanban", "fa-columns", keywords="board enquiries"),
    Command("Calendar", RIGBOARD, "web_calendar", "fa-calendar", keywords="dates schedule"),
    Command("Event Archive", RIGBOARD, "event_archive", "fa-book", keywords="past old history"),
    Command(
        "Recent Changes",
        RIGBOARD,
        "activity_table",
        "fa-random",
        permission="RIGS.view_event",
        keywords="activity history edits",
    ),
    Command(
        "All Recent Changes",
        RIGBOARD,
        "activity_all",
        "fa-history",
        permission="RIGS.view_event",
        keywords="activity history edits everything audit",
    ),
    Command(
        "H&S Overview",
        RIGBOARD,
        "hs_list",
        "fa-hard-hat",
        permission="RIGS.view_riskassessment",
        keywords="health safety risk assessments checklists power",
    ),
    Command("Check Out", RIGBOARD, "event_checkout", "fa-user-clock", check=_checked_in, keywords="checkin leave"),
    Command(
        "Check-in Report",
        RIGBOARD,
        "currently_checked_in",
        "fa-clipboard-list",
        check=_superuser,
        keywords="checked in crew who",
    ),
    Command("New Event", CREATE, "event_create", "fa-plus", permission="RIGS.add_event", keywords="add rig create"),
    Command(
        "New Enquiry", CREATE, "enquiry_create", "fa-lightbulb", permission="RIGS.add_event", keywords="add request"
    ),
    Command(
        "New Person",
        CREATE,
        "person_create",
        "fa-user-plus",
        permission="RIGS.add_person",
        keywords="add client contact",
    ),
    Command(
        "New Organisation",
        CREATE,
        "organisation_create",
        "fa-building",
        permission="RIGS.add_organisation",
        keywords="add client society company",
    ),
    Command(
        "New Venue", CREATE, "venue_create", "fa-map-marker-alt", permission="RIGS.add_venue", keywords="add location"
    ),
    Command("New Asset", CREATE, "asset_create", "fa-tag", permission="assets.add_asset", keywords="add kit"),
    Command(
        "New Supplier",
        CREATE,
        "supplier_create",
        "fa-parachute-box",
        permission="assets.add_supplier",
        keywords="add shop vendor",
    ),
    Command(
        "New Cable Type",
        CREATE,
        "cable_type_create",
        "fa-plug",
        permission="assets.add_cable_type",
        keywords="add connector",
    ),
    Command(
        "Log Training Session",
        CREATE,
        "session_log",
        "fa-chalkboard-teacher",
        check=_can_log_training,
        keywords="add training pass out",
    ),
    Command(
        "Invoice Dashboard",
        FINANCE,
        "invoice_dashboard",
        "fa-chart-line",
        permission="RIGS.view_invoice",
        keywords="money finance stats",
    ),
    Command(
        "Invoices Waiting",
        FINANCE,
        "invoice_waiting",
        "fa-briefcase",
        permission="RIGS.add_invoice",
        keywords="to invoice money",
    ),
    Command(
        "Outstanding Invoices",
        FINANCE,
        "invoice_list",
        "fa-pound-sign",
        permission="RIGS.view_invoice",
        keywords="unpaid money owed",
    ),
    Command(
        "Invoice Archive",
        FINANCE,
        "invoice_archive",
        "fa-book",
        permission="RIGS.view_invoice",
        keywords="paid old money",
    ),
    Command("People", CONTACTS, "person_list", "fa-user", permission="RIGS.view_person", keywords="clients contacts"),
    Command(
        "Organisations",
        CONTACTS,
        "organisation_list",
        "fa-building",
        permission="RIGS.view_organisation",
        keywords="clients societies companies",
    ),
    Command(
        "Venues", CONTACTS, "venue_list", "fa-map-marker-alt", permission="RIGS.view_venue", keywords="locations places"
    ),
    Command("Asset List", ASSETS, "asset_index", "fa-tag", keywords="kit equipment inventory"),
    Command("Cable List", ASSETS, "cable_list", "fa-plug", keywords="cables leads"),
    Command("Cable Types", ASSETS, "cable_type_list", "fa-project-diagram", keywords="connectors"),
    Command("Supplier List", ASSETS, "supplier_list", "fa-parachute-box", keywords="shops vendors"),
    Command(
        "Audit Assets",
        ASSETS,
        "asset_audit_list",
        "fa-clipboard-check",
        permission="assets.change_asset",
        keywords="check stocktake",
    ),
    Command(
        "Asset Changes",
        ASSETS,
        "assets_activity_table",
        "fa-random",
        permission="assets.view_asset",
        keywords="activity history edits",
    ),
    Command(
        "My Training Record",
        TRAINING,
        "trainee_detail",
        "fa-file-signature",
        url_kwargs=lambda request: {"pk": request.user.pk},
        keywords="me qualifications",
    ),
    Command("Trainee List", TRAINING, "trainee_list", "fa-users", keywords="people members"),
    Command("Level List", TRAINING, "level_list", "fa-layer-group", keywords="training levels technician supervisor"),
    Command("Item List", TRAINING, "item_list", "fa-sitemap", keywords="training items skills"),
    Command(
        "Training Changes",
        TRAINING,
        "training_activity_table",
        "fa-random",
        permission="training.view_trainingitemqualification",
        keywords="activity history edits",
    ),
    Command("My Profile", ACCOUNT, "profile_detail", "fa-id-badge", keywords="me account user"),
    Command("Edit Profile", ACCOUNT, "profile_update_self", "fa-user-edit", keywords="me account settings"),
    Command("Change Password", ACCOUNT, "password_change", "fa-key", keywords="security"),
    Command("Badges", ACCOUNT, "badge_list", "fa-award", check=_badges_visible, keywords="achievements"),
    Command(
        "Badge Leaderboard",
        ACCOUNT,
        "badge_leaderboard",
        "fa-trophy",
        check=_badges_visible,
        keywords="achievements top",
    ),
    Command("Tech Rider", ACCOUNT, "tech_rider", "fa-scroll", check=_tech_rider_visible, keywords="stats me"),
    Command("Django Admin", ACCOUNT, "admin:index", "fa-cogs", check=_staff, keywords="backend database"),
    Command("Log Out", ACCOUNT, "logout", "fa-sign-out-alt", method="post", keywords="sign out exit"),
    Command("What's New", HELP, "changelog", "fa-gift", keywords="changelog updates release"),
    Command("Search Help", HELP, "search_help", "fa-question-circle", keywords="syntax"),
]


def commands_for(request):
    if not request.user.is_authenticated:
        return []
    return [command.as_dict(request) for command in COMMANDS if command.allowed(request)]
