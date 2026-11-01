import hmac
import re

from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from RIGS import models

STOPWORDS = {"the", "of", "and", "at", "in", "a", "an", "for", "to"}
MAX_RESULTS = 10


def _authenticate(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or ":" not in header:
        return None
    pk, _, key = header[len("Bearer ") :].partition(":")
    if not pk.isdigit() or not key:
        return None
    user = models.Profile.objects.filter(pk=int(pk), is_active=True).first()
    if user and user.api_key and hmac.compare_digest(user.api_key, key):
        return user
    return None


def _tokens(query):
    return [t for t in re.findall(r"[\w']+", query.lower()) if len(t) >= 2 and t not in STOPWORDS]


def _rank(queryset, query, name_getter=lambda o: o.name):
    tokens = _tokens(query)
    if not tokens:
        return []
    condition = Q()
    for token in tokens:
        condition |= Q(name__icontains=token)
    scored = []
    for obj in queryset.filter(condition)[:200]:
        name = name_getter(obj).lower()
        hits = sum(token in name for token in tokens)
        exact = name == query.strip().lower()
        scored.append((exact, hits, hits / len(tokens), -len(name), obj))
    scored.sort(key=lambda s: s[:4], reverse=True)
    return [s[4] for s in scored[:MAX_RESULTS]]


def _venue(v):
    return {"id": v.pk, "name": v.name, "address": " ".join(v.address.split())[:120]}


def _organisation(o):
    return {"id": o.pk, "name": o.name, "email": o.email}


def _person(p):
    return {
        "id": p.pk,
        "name": p.name,
        "email": p.email,
        "organisations": [org.name for org, _ in p.organisations[:3]],
    }


KINDS = {
    "venues": (models.Venue, "RIGS.view_venue", _venue),
    "organisations": (models.Organisation, "RIGS.view_organisation", _organisation),
    "people": (models.Person, "RIGS.view_person", _person),
}


class LookupView(View):
    def get(self, request, kind):
        user = _authenticate(request)
        if user is None:
            return JsonResponse({"error": "unauthorised"}, status=403)
        if kind not in KINDS:
            return JsonResponse({"error": "unknown kind"}, status=404)
        model, permission, serialise = KINDS[kind]
        if not user.has_perm(permission):
            return JsonResponse({"error": "forbidden"}, status=403)

        email = request.GET.get("email", "").strip()
        query = request.GET.get("q", "").strip()
        if email and kind in ("people", "organisations"):
            results = list(model.objects.filter(email__iexact=email)[:MAX_RESULTS])
        elif query:
            results = _rank(model.objects.all(), query)
        else:
            return JsonResponse({"error": "q or email is required"}, status=400)
        return JsonResponse({"results": [serialise(o) for o in results]})
