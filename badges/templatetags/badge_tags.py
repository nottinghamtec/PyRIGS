from django import template

from badges import views
from badges.models import BadgeSettings

register = template.Library()


@register.simple_tag(takes_context=True)
def badges_visible(context):
    return views.badges_visible(context["request"].user)


@register.simple_tag(takes_context=True)
def tech_rider_visible(context):
    return views.tech_rider_visible(context["request"].user)


@register.inclusion_tag("badges/partials/badge_shelf.html", takes_context=True)
def badge_shelf(context, profile):
    settings = BadgeSettings.load()
    user = context["request"].user
    awards = [award for award in profile.badge_awards.all() if award.badge]
    return {
        "visible": views.badges_visible(user, settings),
        "preview": not settings.badges_live,
        "awards": awards,
        "profile": profile,
        "tech_rider": views.tech_rider_visible(user, settings) and (profile.pk == user.pk or user.is_superuser),
    }
