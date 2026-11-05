from functools import reduce
from operator import add

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models

SEARCH_CONFIG = "rigs"


def search_vector_field(**weighted_fields):
    """A stored tsvector column built from {field_name: weight}, kept up to date by Postgres."""
    vectors = [SearchVector(field, weight=weight, config=SEARCH_CONFIG) for field, weight in weighted_fields.items()]
    return models.GeneratedField(
        expression=reduce(add, vectors),
        output_field=SearchVectorField(),
        db_persist=True,
        editable=False,
        serialize=False,
    )


def search_indexes(prefix, trigram_fields=()):
    indexes = [GinIndex(fields=["search_vector"], name=f"{prefix}_search_idx")]
    indexes += [
        GinIndex(fields=[field], opclasses=["gin_trgm_ops"], name=f"{prefix}_{field}_trgm"[:30])
        for field in trigram_fields
    ]
    return indexes
