from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

import yaml


@dataclass
class Config:
    artists: List[str]
    countries: List[str]
    discord_webhook_url: str
    poll_interval_minutes: int = 30
    ticketmaster_api_key: str = ""
    use_bandsintown: bool = False
    bandsintown_app_id: str = ""
    near_city: str | None = None
    radius_km: int = 0
    db_path: str = "data/events.db"
    notify_on_change: bool = True  # ook melden bij prijs/status-wijziging, niet alleen nieuwe events


def load_config(path: str = "config.yaml") -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Config-bestand '{path}' niet gevonden. Kopieer config.example.yaml naar "
            f"config.yaml en vul je gegevens in."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Env vars overschrijven config.yaml, handig voor secrets in Docker.
    ticketmaster_key = os.environ.get("TICKETMASTER_API_KEY", raw.get("ticketmaster_api_key", ""))
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL", raw.get("discord_webhook_url", ""))
    bandsintown_app_id = os.environ.get("BANDSINTOWN_APP_ID", raw.get("bandsintown_app_id", ""))

    if not raw.get("artists"):
        raise ValueError("Config mist 'artists': geef minstens één artiest op.")
    if not discord_webhook:
        raise ValueError("Config mist 'discord_webhook_url' (of env var DISCORD_WEBHOOK_URL).")
    if not ticketmaster_key:
        raise ValueError("Config mist 'ticketmaster_api_key' (of env var TICKETMASTER_API_KEY).")

    return Config(
        artists=raw["artists"],
        countries=raw.get("countries", ["NL"]),
        discord_webhook_url=discord_webhook,
        poll_interval_minutes=raw.get("poll_interval_minutes", 30),
        ticketmaster_api_key=ticketmaster_key,
        use_bandsintown=raw.get("use_bandsintown", False),
        bandsintown_app_id=bandsintown_app_id,
        near_city=raw.get("near_city"),
        radius_km=raw.get("radius_km", 0),
        db_path=raw.get("db_path", "data/events.db"),
        notify_on_change=raw.get("notify_on_change", True),
    )
