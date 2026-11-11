from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = "db.duckdb"
    db_init_script_path: str = "init.sql"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
