import json
import logging
import time
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from reversion import revisions as reversion

# How long a claimed form render stays remembered
NONCE_TTL = 300

IN_FLIGHT = "in-flight"

IN_FLIGHT_PAGE = (
    "<!doctype html><title>Already saving</title>"
    "<p>This form has already been submitted and is still being saved. "
    "Please don't submit it again; check back in a moment.</p>"
)


class DuplicateSubmissionMiddleware:
    """
    Stops a form being processed twice when it is submitted twice (a double click on a slow page).

    Django masks the CSRF token with a fresh random salt every time it is rendered, so the
    ``csrfmiddlewaretoken`` posted by a form is unique to that one render of that form. We use it as a nonce:
    the first POST claims it, and any later POST with the same value never reaches the view. If the first has
    finished successfully it is answered with the first one's redirect; if the first is still running it is
    answered straight away (never waiting, so duplicates can't tie up workers) with a short notice.

    Only successful redirects are remembered, so a form that failed validation, or errored, can be re-submitted,
    and a re-rendered form carries a new token anyway. Needs a shared cache to work across processes.

    Must sit after ``CsrfViewMiddleware`` so unauthenticated junk can't claim nonces.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def cache_key(token):
        return f"form-nonce:{token}"

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception:
            self.release(request)
            raise
        return self.record(request, response)

    def process_view(self, request, view_func, view_args, view_kwargs):
        token = request.POST.get("csrfmiddlewaretoken") if request.method == "POST" else None
        if not token:
            return None

        key = self.cache_key(token)
        if cache.add(key, IN_FLIGHT, NONCE_TTL):
            request._form_nonce_key = key
            return None

        state = cache.get(key)
        if state is None:
            # Released or expired between the add and the get, so treat this as a genuine retry
            if cache.add(key, IN_FLIGHT, NONCE_TTL):
                request._form_nonce_key = key
            return None
        if state == IN_FLIGHT:
            return HttpResponse(IN_FLIGHT_PAGE, status=409)
        return HttpResponseRedirect(state)

    def record(self, request, response):
        key = getattr(request, "_form_nonce_key", None)
        if key is None:
            return response
        if response.status_code in (301, 302, 303, 307, 308) and response.has_header("Location"):
            cache.set(key, response["Location"], NONCE_TTL)
        else:
            cache.delete(key)
        return response

    def release(self, request):
        key = getattr(request, "_form_nonce_key", None)
        if key is not None:
            cache.delete(key)


class RevisionUserMiddleware:
    """Tells reversion who is acting as soon as they're known, as its own middleware only does so after the view"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if reversion.is_active() and request.user.is_authenticated:
            reversion.set_user(request.user)
        return self.get_response(request)


access_logger = logging.getLogger("pyrigs.access")

# Everything an access log line can contain. Each takes (request, response, duration in ms) and the line is made of
# the ones named in settings.ACCESS_LOG_FIELDS, in that order.
ACCESS_LOG_FIELD_EXTRACTORS = {
    "time": lambda request, response, ms: datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    "ip": lambda request, response, ms: client_ip(request),
    "user_id": lambda request, response, ms: authenticated_user(request) and authenticated_user(request).pk,
    "username": lambda request, response, ms: (
        authenticated_user(request) and authenticated_user(request).get_username()
    ),
    "method": lambda request, response, ms: request.method,
    "path": lambda request, response, ms: request.path,
    "status": lambda request, response, ms: response.status_code,
    "duration_ms": lambda request, response, ms: ms,
    "bytes": lambda request, response, ms: int(response.get("Content-Length") or 0) or None,
    "query": lambda request, response, ms: request.META.get("QUERY_STRING", ""),
    "host": lambda request, response, ms: request.META.get("HTTP_HOST", ""),
    "user_agent": lambda request, response, ms: request.META.get("HTTP_USER_AGENT", ""),
    "referer": lambda request, response, ms: request.META.get("HTTP_REFERER", ""),
    "view": lambda request, response, ms: request.resolver_match.view_name if request.resolver_match else None,
    "forwarded_for": lambda request, response, ms: request.META.get("HTTP_X_FORWARDED_FOR", ""),
    "http_version": lambda request, response, ms: (
        request.META.get("HTTP_X_HTTP_VERSION") or request.META.get("SERVER_PROTOCOL")
    ),
    "is_staff": lambda request, response, ms: bool(
        authenticated_user(request) and authenticated_user(request).is_staff
    ),
}


def client_ip(request):
    """nginx overwrites X-Real-IP with the address that connected to it, so a client can't spoof it in production"""
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def authenticated_user(request):
    """The logged-in user, or failing that the user an API key identified (set as ``request.api_user``)"""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user
    return getattr(request, "api_user", None)


class AccessLogMiddleware:
    """
    Logs one JSON line per request to the ``pyrigs.access`` logger, including who made it.

    Sits outermost so it sees every response, including redirects and errors from other middleware. The user is read
    after the response is built, so a request that logs in is attributed to the new user and one that logs out is
    anonymous. Static files are skipped.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.static_prefix = settings.STATIC_URL

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        if not request.path.startswith(self.static_prefix):
            self.log(request, response, round((time.monotonic() - started) * 1000, 1))
        return response

    @staticmethod
    def log(request, response, duration_ms):
        entry = {
            name: ACCESS_LOG_FIELD_EXTRACTORS[name](request, response, duration_ms)
            for name in settings.ACCESS_LOG_FIELDS
        }
        access_logger.info(json.dumps(entry, ensure_ascii=False))
