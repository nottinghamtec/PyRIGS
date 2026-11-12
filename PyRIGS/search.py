import math
import re
from dataclasses import dataclass, field
from functools import reduce
from operator import add, or_
from typing import Callable

from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank, TrigramWordSimilarity
from django.db import connection
from django.db.models import Case, F, FloatField, Func, IntegerField, Q, TextField, Value, When
from django.db.models.functions import Cast, Concat, Exp
from django.utils.html import escape
from django.utils.safestring import mark_safe

from PyRIGS.search_fields import SEARCH_CONFIG

EXACT_MATCH_SCORE = 10.0
TRIGRAM_WEIGHT = 0.5
RECENCY_FLOOR = 0.4
RECENCY_HALF_LIFE_DAYS = 365

HIGHLIGHT_START = ""
HIGHLIGHT_STOP = ""

INTEGER = re.compile(r"^\d+$")
EVENT_ID = re.compile(r"^[Nn]0*(\d+)$")
INVOICE_ID = re.compile(r"^#0*(\d+)$")
TRAINING_ITEM_ID = re.compile(r"^(\d+)\.(\d+)$")
PHONE = re.compile(r"^\+?[\d ]{3,}$")
WORD = re.compile(r"[^\W\d_]{3,}")
NEGATION = re.compile(r'(?:^|(?<=\s))-("[^"]*"|[^\s"]+)')


@dataclass
class ParsedQuery:
    """The query as typed, plus the parts of it that should be matched loosely and highlighted (not the -negations)."""

    text: str
    positive: str
    negated: list

    @classmethod
    def parse(cls, query):
        text = (query or "").strip()
        negated = [term for term in NEGATION.findall(text) if term.strip('"').strip()]
        words = NEGATION.sub(" ", text).split()
        while words and words[0].lower() == "or":
            words.pop(0)
        while words and words[-1].lower() == "or":
            words.pop()
        positive = " ".join(words)
        return cls(text=text, positive=positive, negated=negated)

    @property
    def search_query(self):
        return make_search_query(self.text)

    @property
    def highlight_query(self):
        return make_search_query(self.positive)

    @property
    def excluded_query(self):
        if not self.negated:
            return None
        return reduce(or_, (make_search_query(term) for term in self.negated))


class DaysFromToday(Func):
    template = "abs(current_date - %(expressions)s)"
    output_field = IntegerField()


def recency(date_field):
    """1 for something happening today, decaying towards RECENCY_FLOOR the further away it is in either direction."""
    decay = Exp(Value(-math.log(2) / RECENCY_HALF_LIFE_DAYS) * Cast(DaysFromToday(F(date_field)), FloatField()))
    return Value(RECENCY_FLOOR) + Value(1 - RECENCY_FLOOR) * decay


def _pk_match(query, *patterns, lookup="pk"):
    for pattern in patterns:
        match = pattern.match(query)
        if match:
            return Q(**{lookup: int(match.group(match.lastindex or 0))})
    return None


def _contact_exact(query):
    exact = _pk_match(query, INTEGER)
    if PHONE.match(query):
        phone = Q(phone__startswith=query) | Q(phone__endswith=query)
        exact = phone if exact is None else exact | phone
    return exact


def _event_exact(query):
    return _pk_match(query, INTEGER, EVENT_ID)


def _invoice_exact(query):
    exact = [
        _pk_match(query, INVOICE_ID, INTEGER),
        _pk_match(query, EVENT_ID, INTEGER, lookup="event__pk"),
    ]
    exact = [q for q in exact if q is not None]
    return reduce(or_, exact) if exact else None


def _asset_exact(query):
    return Q(asset_id__iexact=query) | Q(serial_number__iexact=query)


def _trainee_exact(query):
    exact = Q(initials__iexact=query)
    pk = _pk_match(query, INTEGER)
    return exact | pk if pk is not None else exact


def _training_item_exact(query):
    match = TRAINING_ITEM_ID.match(query)
    if match:
        return Q(category__reference_number=int(match.group(1)), reference_number=int(match.group(2)))
    return None


@dataclass
class Source:
    kind: str
    label: str
    get_queryset: Callable
    title: Callable
    vector: str = "search_vector"
    trigram_fields: tuple = ()
    snippet_fields: tuple = ()
    recency_field: str | None = None
    exact: Callable | None = None
    permission: str | None = None
    select_related: tuple = ()
    prefix: Callable = field(default=lambda obj: "")

    def visible_to(self, user):
        return self.permission is None or user.has_perm(self.permission)

    def ranked(self, parsed):
        search_query = parsed.search_query
        loose = parsed.positive
        relevance = [SearchRank(F(self.vector), search_query)]
        match = Q(**{f"{self.vector}": search_query})
        for trigram_field in self.trigram_fields:
            relevance.append(Value(TRIGRAM_WEIGHT) * TrigramWordSimilarity(loose, trigram_field))
            match |= Q(**{f"{trigram_field}__trigram_word_similar": loose})
        exact = self.exact(loose) if self.exact else None
        if exact is not None:
            relevance.append(Case(When(exact, then=Value(EXACT_MATCH_SCORE)), default=Value(0.0)))
            match |= exact
        if parsed.excluded_query is not None:
            match &= ~Q(**{f"{self.vector}": parsed.excluded_query})

        score = reduce(add, relevance)
        if self.recency_field:
            score = score * recency(self.recency_field)

        return (
            self.get_queryset()
            .filter(match)
            .order_by()
            .annotate(kind=Value(self.kind), obj_id=F("pk"), score=Cast(score, FloatField()))
            .values("kind", "obj_id", "score")
        )

    def hydrate(self, ids, search_query):
        highlight = {"config": SEARCH_CONFIG, "start_sel": HIGHLIGHT_START, "stop_sel": HIGHLIGHT_STOP}
        annotations = {"search_title": SearchHeadline(self.title(), search_query, highlight_all=True, **highlight)}
        if self.snippet_fields:
            parts = sum(([F(name), Value(" ")] for name in self.snippet_fields), [])[:-1]
            text = Concat(*parts, output_field=TextField()) if len(parts) > 1 else parts[0]
            annotations["search_snippet"] = SearchHeadline(
                text,
                search_query,
                max_words=30,
                min_words=12,
                max_fragments=2,
                fragment_delimiter=" … ",
                **highlight,
            )
        return self.get_queryset().filter(pk__in=ids).select_related(*self.select_related).annotate(**annotations)


def _sources():
    from assets.models import Asset, Supplier
    from RIGS.models import Event, Invoice, Organisation, Person, Venue
    from training.models import Trainee, TrainingItem

    def contact(kind, label, model):
        return Source(
            kind=kind,
            label=label,
            get_queryset=model.objects.all,
            title=lambda: F("name"),
            trigram_fields=("name",),
            snippet_fields=("notes", "address", "email"),
            exact=_contact_exact,
        )

    return [
        Source(
            kind="event",
            label="Event",
            get_queryset=Event.objects.all,
            title=lambda: F("name"),
            trigram_fields=("name",),
            snippet_fields=("description", "notes"),
            recency_field="start_date",
            exact=_event_exact,
            select_related=("person", "organisation", "venue", "mic"),
            prefix=lambda event: f"{event.display_id} |",
        ),
        contact("person", "Person", Person),
        contact("organisation", "Organisation", Organisation),
        contact("venue", "Venue", Venue),
        Source(
            kind="invoice",
            label="Invoice",
            get_queryset=Invoice.objects.all,
            title=lambda: F("event__name"),
            vector="event__search_vector",
            trigram_fields=("event__name",),
            recency_field="event__start_date",
            exact=_invoice_exact,
            permission="RIGS.view_invoice",
            select_related=("event",),
            prefix=lambda invoice: f"{invoice.display_id} for {invoice.event.display_id} |",
        ),
        Source(
            kind="asset",
            label="Asset",
            get_queryset=Asset.objects.all,
            title=lambda: F("description"),
            trigram_fields=("description", "nickname"),
            snippet_fields=("nickname", "comments"),
            exact=_asset_exact,
            select_related=("category", "status"),
            prefix=lambda asset: f"{asset.asset_id} |",
        ),
        contact("supplier", "Supplier", Supplier),
        Source(
            kind="trainee",
            label="Trainee",
            get_queryset=Trainee.objects.all,
            title=lambda: Concat(F("first_name"), Value(" "), F("last_name"), output_field=TextField()),
            trigram_fields=("first_name", "last_name"),
            exact=_trainee_exact,
        ),
        Source(
            kind="training_item",
            label="Training Item",
            get_queryset=TrainingItem.objects.all,
            title=lambda: F("name"),
            trigram_fields=("name",),
            snippet_fields=("description",),
            exact=_training_item_exact,
            select_related=("category",),
            prefix=lambda item: item.display_id,
        ),
    ]


def make_search_query(query):
    return SearchQuery(query, search_type="websearch", config=SEARCH_CONFIG)


def search(query, user):
    """A single ranked query over everything the user may see, as rows of {kind, obj_id, score}."""
    parsed = ParsedQuery.parse(query)
    sources = [source for source in _sources() if source.visible_to(user)]
    if not parsed.positive or not sources:
        return []

    branches = [source.ranked(parsed) for source in sources]
    return branches[0].union(*branches[1:], all=True).order_by("-score", "kind", "-obj_id")


def search_events(query, limit=20):
    """Events matching the query (by text, or by exact id such as 123 or N00123) as a list, best match first."""
    from RIGS.models import Event

    parsed = ParsedQuery.parse(query)
    if not parsed.positive:
        return []
    source = next(s for s in _sources() if s.kind == "event")
    ids = [row["obj_id"] for row in source.ranked(parsed).order_by("-score", "-obj_id")[:limit]]
    events = Event.objects.select_related("person", "organisation", "venue").in_bulk(ids)
    return [events[pk] for pk in ids if pk in events]


def _highlight(text):
    if not text:
        return ""
    return mark_safe(escape(text).replace(HIGHLIGHT_START, "<mark>").replace(HIGHLIGHT_STOP, "</mark>"))


@dataclass
class Result:
    object: object
    kind: str
    label: str
    prefix: str
    title: str
    snippet: str
    score: float


def hydrate(rows, query):
    """Turn a page of {kind, obj_id, score} rows into Results, keeping their order."""
    rows = list(rows)
    sources = {source.kind: source for source in _sources()}
    search_query = ParsedQuery.parse(query).highlight_query
    objects = {}
    for kind in {row["kind"] for row in rows}:
        ids = [row["obj_id"] for row in rows if row["kind"] == kind]
        for obj in sources[kind].hydrate(ids, search_query):
            objects[(kind, obj.pk)] = obj

    results = []
    for row in rows:
        obj = objects.get((row["kind"], row["obj_id"]))
        if obj is None:
            continue
        source = sources[row["kind"]]
        results.append(
            Result(
                object=obj,
                kind=source.kind,
                label=source.label,
                prefix=source.prefix(obj),
                title=_highlight(obj.search_title) or str(obj),
                snippet=_highlight(getattr(obj, "search_snippet", "")),
                score=row["score"],
            )
        )
    return results


def refresh_vocabulary():
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY search_vocabulary")
        cursor.execute("SELECT count(*) FROM search_vocabulary")
        return cursor.fetchone()[0]


def suggest(query):
    """Replace words that never appear in the data with the closest word that does, or None if nothing changes."""
    words = {word.lower() for word in WORD.findall(query or "")}
    corrections = {}
    with connection.cursor() as cursor:
        for word in words:
            cursor.execute(
                """
                WITH typed AS (SELECT lower(unaccent(%s)) AS word)
                SELECT search_vocabulary.word, search_vocabulary.word = typed.word
                FROM search_vocabulary, typed
                WHERE search_vocabulary.word %% typed.word
                ORDER BY search_vocabulary.word = typed.word DESC,
                    similarity(search_vocabulary.word, typed.word) DESC,
                    frequency DESC
                LIMIT 1
                """,
                [word],
            )
            row = cursor.fetchone()
            if row and not row[1]:
                corrections[word] = row[0]

    if not corrections:
        return None
    pattern = re.compile(r"\b(" + "|".join(re.escape(word) for word in corrections) + r")\b", re.IGNORECASE)
    return pattern.sub(lambda match: corrections[match.group(0).lower()], query)
