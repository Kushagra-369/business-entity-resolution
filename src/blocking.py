from pathlib import Path
import re
import unicodedata
import duckdb


DATASET_ROOT = Path.home() / "Downloads" / "student_resource"
DB_PATH = "entity_resolution.duckdb"


def normalize_text(value):
    if value is None:
        return ""

    value = str(value)
    value = unicodedata.normalize("NFKC", value).lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()

    return value

def create_normalized_tables(con):
    for source in ["source1", "source2", "source3"]:

        table = f"train_{source}"
        normalized = f"norm_{source}"

        print(f"Normalizing {table}...")

        con.execute(f"""
            CREATE OR REPLACE TABLE {normalized} AS
            SELECT
                entity_id,
                business_name,
                business_address,
                country,

                lower(
                    trim(
                        coalesce(country, '')
                    )
                ) AS country_norm,

                lower(
                    trim(
                        regexp_replace(
                            coalesce(business_name, ''),
                            '[[:punct:]]',
                            ' ',
                            'g'
                        )
                    )
                ) AS name_norm,

                lower(
                    trim(
                        regexp_replace(
                            coalesce(business_address, ''),
                            '[[:punct:]]',
                            ' ',
                            'g'
                        )
                    )
                ) AS address_norm

            FROM {table}
        """)

        print(
            f"{normalized}: "
            f"{con.execute(f'SELECT COUNT(*) FROM {normalized}').fetchone()[0]:,}"
        )

def create_blocking_keys(con):

    for source in ["source1", "source2", "source3"]:

        table = f"norm_{source}"

        con.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS name_key VARCHAR
        """)

        con.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS address_key VARCHAR
        """)

        # First meaningful token from business name
        con.execute(f"""
            UPDATE {table}
            SET name_key =
                CASE
                    WHEN name_norm = '' THEN ''
                    ELSE split_part(name_norm, ' ', 1)
                END
        """)

        # First numeric token if available, otherwise first address token
        con.execute(f"""
            UPDATE {table}
            SET address_key =
                CASE
                    WHEN regexp_extract(address_norm, '[0-9]+') != ''
                    THEN regexp_extract(address_norm, '[0-9]+')
                    ELSE split_part(address_norm, ' ', 1)
                END
        """)


def build_candidate_query():

    return """
        SELECT DISTINCT
            s1.entity_id AS source1_entity_id,
            s2.entity_id AS matched_entity_id,
            'S2' AS matched_source
        FROM norm_source1 s1
        JOIN norm_source2 s2
          ON s1.country_norm = s2.country_norm
         AND s1.country_norm <> ''
         AND (
                (
                    s1.name_key <> ''
                    AND s1.name_key = s2.name_key
                )
                OR
                (
                    s1.address_key <> ''
                    AND s1.address_key = s2.address_key
                )
             )

        UNION ALL

        SELECT DISTINCT
            s1.entity_id AS source1_entity_id,
            s3.entity_id AS matched_entity_id,
            'S3' AS matched_source
        FROM norm_source1 s1
        JOIN norm_source3 s3
          ON s1.country_norm = s3.country_norm
         AND s1.country_norm <> ''
         AND (
                (
                    s1.name_key <> ''
                    AND s1.name_key = s3.name_key
                )
                OR
                (
                    s1.address_key <> ''
                    AND s1.address_key = s3.address_key
                )
             )
    """


def main():

    con = duckdb.connect(DB_PATH)

    create_normalized_tables(con)
    create_blocking_keys(con)

    print("\nTesting candidate generation...")

    query = build_candidate_query()

    count = con.execute(
        f"SELECT COUNT(*) FROM ({query}) candidates"
    ).fetchone()[0]

    print(f"Candidate pairs: {count:,}")

    con.close()


if __name__ == "__main__":
    main()