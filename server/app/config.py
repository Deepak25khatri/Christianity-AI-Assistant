from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    jwt_secret: str = Field(default="dev-insecure-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")

    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="christianity_kb", alias="QDRANT_COLLECTION")

    sqlite_path: str = Field(default="/data/christianity.db", alias="SQLITE_PATH")

    chat_model: str = Field(default="gpt-4o-mini", alias="CHAT_MODEL")
    embed_model: str = Field(default="text-embedding-3-small", alias="EMBED_MODEL")
    image_model: str = Field(default="gpt-image-1", alias="IMAGE_MODEL")

    rate_limit_per_min: int = Field(default=30, alias="RATE_LIMIT_PER_MIN")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost", alias="CORS_ORIGINS")

    canonical_bible_path: str = Field(default="/data/bible_canonical.json", alias="CANONICAL_BIBLE_PATH")
    bm25_index_path: str = Field(default="/data/bm25.pkl", alias="BM25_INDEX_PATH")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
