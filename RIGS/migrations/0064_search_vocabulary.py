from django.db import migrations

VOCABULARY_SOURCES = [
    ('"RIGS_event"', ["name", "description"]),
    ('"RIGS_person"', ["name"]),
    ('"RIGS_organisation"', ["name"]),
    ('"RIGS_venue"', ["name"]),
    ('"RIGS_profile"', ["first_name", "last_name"]),
    ('"assets_supplier"', ["name"]),
    ('"assets_asset"', ["description", "nickname"]),
    ('"training_trainingitem"', ["name", "description"]),
]

WORDS = "\n    UNION ALL ".join(
    f"SELECT regexp_split_to_table(lower(unaccent('unaccent'::regdictionary, concat_ws(' ', {', '.join(columns)}))), "
    f"'[^[:alpha:]]+') AS word FROM {table}"
    for table, columns in VOCABULARY_SOURCES
)

CREATE = [
    f"""
    CREATE MATERIALIZED VIEW search_vocabulary AS
    SELECT word, count(*) AS frequency
    FROM ({WORDS}) AS words
    WHERE length(word) >= 3
    GROUP BY word
    """,
    "CREATE UNIQUE INDEX search_vocabulary_word ON search_vocabulary (word)",
    "CREATE INDEX search_vocabulary_word_trgm ON search_vocabulary USING gin (word gin_trgm_ops)",
]


class Migration(migrations.Migration):
    dependencies = [
        ("RIGS", "0063_search_vectors"),
        ("assets", "0030_search_vectors"),
        ("training", "0012_search_vectors"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE, reverse_sql="DROP MATERIALIZED VIEW search_vocabulary"),
    ]
