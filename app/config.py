import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv


class AppConfig(BaseModel):
    feeds: List[str] = Field(default_factory=list)
    process_delay_seconds: int = 15
    feed_refresh_seconds: int = 300
    storage_ttl_seconds: int = 86400
    log_dir: str = "logs"

    # LLM (Tiri/Groq)
    tiri_base_url: str
    tiri_api_keys: List[str]

    # Platforms
    platforms: List[str] = Field(default_factory=list)

    # Facebook (multi-account)
    facebook_page_ids: List[str] = Field(default_factory=list)
    facebook_page_tokens: List[str] = Field(default_factory=list)

    # Twitter/X (multi-account)
    twitter_bearer_tokens: List[str] = Field(default_factory=list)


def load_config() -> AppConfig:
    load_dotenv()

    feeds_env = os.getenv("FEEDS", "").strip()
    feeds = [u.strip() for u in feeds_env.split(",") if u.strip()]

    tiri_keys_env = os.getenv("TIRI_API_KEYS", "").strip()
    tiri_api_keys = [k.strip() for k in tiri_keys_env.split(",") if k.strip()]

    platforms_env = os.getenv("PLATFORMS", "facebook").strip()
    platforms = [p.strip().lower() for p in platforms_env.split(",") if p.strip()]

    fb_ids_env = os.getenv("FACEBOOK_PAGE_IDS", "").strip()
    facebook_page_ids = [v.strip() for v in fb_ids_env.split(",") if v.strip()]

    fb_tokens_env = os.getenv("FACEBOOK_PAGE_TOKENS", "").strip()
    facebook_page_tokens = [v.strip() for v in fb_tokens_env.split(",") if v.strip()]

    twitter_tokens_env = os.getenv("TWITTER_BEARER_TOKENS", "").strip()
    twitter_bearer_tokens = [v.strip() for v in twitter_tokens_env.split(",") if v.strip()]

    data = {
        "feeds": feeds,
        "process_delay_seconds": int(os.getenv("PROCESS_DELAY_SECONDS", "15")),
        "feed_refresh_seconds": int(os.getenv("FEED_REFRESH_SECONDS", "300")),
        "storage_ttl_seconds": int(os.getenv("STORAGE_TTL_SECONDS", "86400")),
        "log_dir": os.getenv("LOG_DIR", "logs"),
        "tiri_base_url": os.getenv("TIRI_BASE_URL", ""),
        "tiri_api_keys": tiri_api_keys,
        "platforms": platforms,
        "facebook_page_ids": facebook_page_ids,
        "facebook_page_tokens": facebook_page_tokens,
        "twitter_bearer_tokens": twitter_bearer_tokens,
    }

    try:
        return AppConfig(**data)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}")


