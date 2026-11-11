import os
from pathlib import Path

from sqlalchemy.engine import URL


BASE_DIR = Path(__file__).resolve().parent
database_path = os.getenv("SQLITE_DATABASE_PATH")

if database_path:
    SQLITE_DATABASE_PATH = Path(database_path).expanduser().resolve()
else:
    SQLITE_DATABASE_PATH = BASE_DIR / "instance" / "tickets.db"

SQLITE_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "helpdesk-secret-key"
    )
    SQLALCHEMY_DATABASE_URI = str(
        URL.create(
            "sqlite",
            database=str(SQLITE_DATABASE_PATH)
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
