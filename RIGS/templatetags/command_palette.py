import re

from django import template
from django.utils.html import format_html, format_html_join

from PyRIGS.commands import commands_for

register = template.Library()

APPLE_DEVICE = re.compile(r"Macintosh|Mac OS X|iPhone|iPad|iPod")


def is_apple_device(request):
    return bool(request and APPLE_DEVICE.search(request.META.get("HTTP_USER_AGENT", "")))


@register.simple_tag(takes_context=True)
def command_list(context):
    return commands_for(context["request"])


@register.simple_tag(takes_context=True)
def modifier_key(context):
    """⌘ on Apple devices, Ctrl everywhere else."""
    return "⌘" if is_apple_device(context.get("request")) else "Ctrl"


@register.simple_tag(takes_context=True)
def alt_key(context):
    """⌥ on Apple devices, Alt everywhere else."""
    return "⌥" if is_apple_device(context.get("request")) else "Alt"


@register.simple_tag(takes_context=True)
def shortcut_keys(context, *keys):
    """A keyboard shortcut as <kbd> keys, with the modifier key for the viewer's device, e.g. {% shortcut_keys "K" %}."""
    return format_html_join(" ", "<kbd>{}</kbd>", ((key,) for key in (modifier_key(context), *keys)))


@register.simple_tag(takes_context=True)
def shortcut_label(context, key):
    """A compact label such as ⌘K or Ctrl K."""
    modifier = modifier_key(context)
    return format_html("{}{}{}", modifier, "" if modifier == "⌘" else " ", key)
