"""Environment-based API configuration helpers."""

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

def get_api_key() -> Optional[str]:
    """Return configured API key from environment."""
    return os.environ.get("LLM_API")


def get_base_url() -> Optional[str]:
    """Return configured API base URL from environment."""
    return os.environ.get("LLM_URL")


def has_api_config() -> bool:
    """Whether required API environment variables are configured."""
    return bool(get_api_key() and get_base_url())


def resolve_api_config() -> tuple[str, Optional[str], str]:
    """Resolve API key, base URL, and model from environment variables."""
    api_key = get_api_key()
    base_url = get_base_url()
    model = os.environ.get("MODEL")

    if not api_key:
        raise ValueError("LLM_API must be set")
    if not base_url:
        raise ValueError("LLM_URL must be set")
    if not model:
        raise ValueError("MODEL must be set")

    return api_key, base_url, model
