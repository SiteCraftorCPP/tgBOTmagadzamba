from __future__ import annotations

import os
from urllib.parse import quote


def normalize_telegram_proxy(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    lowered = s.lower()
    if lowered.startswith(("http://", "https://", "socks5://", "socks4://")):
        return s

    scheme = os.getenv("TELEGRAM_PROXY_SCHEME", "http").strip().lower() or "http"
    if scheme not in {"http", "https", "socks5", "socks4"}:
        scheme = "http"

    parts = s.split(":")
    if len(parts) < 4:
        return s if "://" in s else None

    host, port, user = parts[0], parts[1], parts[2]
    password = ":".join(parts[3:])
    uq = quote(user, safe="")
    pq = quote(password, safe="")

    if scheme.startswith("socks"):
        return f"{scheme}://{uq}:{pq}@{host}:{port}"
    if scheme == "https":
        scheme = "http"
    return f"http://{uq}:{pq}@{host}:{port}"
