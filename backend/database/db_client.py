import duckdb

from config import settings

# Connection client that will be used everywhere
conn = duckdb.connect(settings.db_path, True)
