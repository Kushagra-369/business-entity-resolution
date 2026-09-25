from pathlib import Path
import duckdb


DATASET_ROOT = Path.home() / "Downloads" / "student_resource"


def build_database(db_path="entity_resolution.duckdb"):
    con = duckdb.connect(db_path)

    train = DATASET_ROOT / "dataset" / "train"

    print("Loading training sources...")

    for source in ["source1", "source2", "source3"]:
        path = train / f"train_{source}.tsv"

        table = f"train_{source}"

        con.execute(f"""
            CREATE OR REPLACE TABLE {table} AS
            SELECT *
            FROM read_csv(
                '{path}',
                delim='\\t',
                header=true,
                ignore_errors=false
            )
        """)

        print(f"{table}: {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:,} rows")

    con.close()


if __name__ == "__main__":
    build_database()