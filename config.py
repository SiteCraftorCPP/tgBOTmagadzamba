import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


from proxy_util import normalize_telegram_proxy


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    bot_username: str
    proxy_url: str | None
    channel_id: int


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = os.getenv("ADMIN_ID", "7600749840").strip()
    bot_username = os.getenv("BOT_USERNAME", "tgBOTmagadzamba_bot").strip().lstrip("@")
    channel_id_raw = os.getenv("CHANNEL_ID", "-1003733210844").strip()
    proxy_raw = (
        os.getenv("TELEGRAM_PROXY") or os.getenv("BOT_PROXY") or ""
    ).strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example.")

    try:
        parsed_admin_id = int(admin_id)
    except ValueError as exc:
        raise RuntimeError("ADMIN_ID must be a number.") from exc

    try:
        parsed_channel_id = int(channel_id_raw)
    except ValueError as exc:
        raise RuntimeError("CHANNEL_ID must be a number.") from exc

    proxy_url = normalize_telegram_proxy(proxy_raw)

    return Config(
        bot_token=bot_token,
        admin_id=parsed_admin_id,
        bot_username=bot_username,
        proxy_url=proxy_url,
        channel_id=parsed_channel_id,
    )
