from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # local | staging | production. Anything but "local" refuses to start on
    # SQLite — see app/db.py.
    environment: str = "local"

    # Local default only. Production sets this to a managed Postgres:
    #   postgresql+psycopg://user:pass@host:5432/nextera
    # That one string decides where the data lives: on the disk of the machine
    # running the app, or in a database it connects to. Only the second lets you
    # replace the machine. Nothing else in the codebase changes.
    database_url: str = "sqlite:///./nextera.db"

    # Required by POST /items when set. Leaving it empty leaves writes open,
    # which is what this demo runs. See app/security.py.
    api_key: str | None = None

    app_name: str = "NextEra Asset Reporting API"
    debug: bool = False


settings = Settings()
