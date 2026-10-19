from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect

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
