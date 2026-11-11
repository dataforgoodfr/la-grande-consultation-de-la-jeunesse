from pathlib import Path

import duckdb

from config import settings

DB_PATH = Path(settings.db_path)
SQL_PATH = Path(settings.db_init_script_path)


def init_database() -> None:
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"Le fichier {SQL_PATH} est introuvable.")

    conn = duckdb.connect(str(DB_PATH))

    try:
        sql_script = SQL_PATH.read_text(encoding="utf-8")
        conn.execute(sql_script)
        print(f"Base de données initialisée avec succès dans {DB_PATH}.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
