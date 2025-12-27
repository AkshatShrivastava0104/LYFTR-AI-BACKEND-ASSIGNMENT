import os
from typing import Optional

class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")

    @classmethod
    def validate(cls) -> bool:
        return cls.WEBHOOK_SECRET is not None and cls.WEBHOOK_SECRET != ""

config = Config()
