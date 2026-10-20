from django import template

from badges import views
from badges.models import BadgeSettings

register = template.Library()


def request_settings(request):
    """The badge settings row, read once per request however many tags ask for it"""
    if not hasattr(request, "_badge_settings"):
        request._badge_settings = BadgeSettings.load()
    return request._badge_settings


@register.simple_tag(takes_context=True)
def badges_visible(context):
    request = context["request"]
    return views.badges_visible(request.user, request_settings(request))


@register.simple_tag(takes_context=True)
def tech_rider_visible(context):
    request = context["request"]
    return views.tech_rider_visible(request.user, request_settings(request))


@register.inclusion_tag("badges/partials/badge_shelf.html", takes_context=True)
def badge_shelf(context, profile):
    settings = request_settings(context["request"])
    user = context["request"].user
    awards = [award for award in profile.badge_awards.all() if award.badge]
    return {
        "visible": views.badges_visible(user, settings),
        "preview": not settings.badges_live,
        "awards": awards,
        "profile": profile,
        "tech_rider": views.tech_rider_visible(user, settings) and (profile.pk == user.pk or user.is_superuser),
    }
