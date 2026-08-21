from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # local | staging | production. Anything but "local" refuses to start on
    # SQLite — see app/db.py.
    environment: str = "local"

    # Local default only. Production sets this to a managed Postgres:
    #   postgresql+psycopg://user:pass@host:5432/nextera
    # That one string is the difference between "data on this box's disk, so the
    # box can never be replaced" and "data over the network, so the servers are
    # disposable." Nothing else in the codebase changes.
    database_url: str = "sqlite:///./nextera.db"

    # Auth is implemented in app/security.py but deliberately not enforced.
    # See the commented wiring in app/main.py and app/routers/items.py.
    api_key: str | None = None

    app_name: str = "NextEra Asset Reporting API"
    debug: bool = False


settings = Settings()
