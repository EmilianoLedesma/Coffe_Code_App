import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    secret_key: str
    coffee_api_url: str
    session_lifetime_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.environ["FLASK_SECRET_KEY"],
            coffee_api_url=os.environ.get("COFFEE_API_URL", "http://localhost:8010"),
            session_lifetime_hours=int(os.environ.get("SESSION_LIFETIME_HOURS", "24")),
        )


settings = Settings.from_env()
