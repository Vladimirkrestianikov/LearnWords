from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="Default OpenAI model")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="Telegram IDs with Admin role")
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///data/learnwords.db",
        description="SQLAlchemy Database URL"
    )
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Max vocabulary file upload in MB")
    RATE_LIMIT_SECONDS: float = Field(default=0.5, description="Throttling rate limit in seconds")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, int, List[Union[int, str]]]) -> List[int]:
        if isinstance(v, (int, str)):
            if isinstance(v, int):
                return [v]
            v = str(v).strip()
            if not v:
                return []
            if "," in v:
                return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
            if v.isdigit():
                return [int(v)]
            return []
        if isinstance(v, list):
            return [int(x) for x in v if str(x).strip().isdigit()]
        return []

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.ADMIN_IDS


settings = Settings()

