"""
Stuurt nette Discord-embeds via een webhook wanneer er een nieuw of
gewijzigd event gevonden is.
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

COLOR_NEW = 0x1DB954       # groen: nieuw event
COLOR_CHANGED = 0xF59E0B   # oranje: bestaand event gewijzigd
COLOR_CANCELLED = 0xE11D48  # rood: geannuleerd/afgelast


def _format_date(date_str: str) -> str:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str[:19] if "T" in date_str else date_str, fmt)
            if "T" in date_str:
                return dt.strftime("%d %B %Y, %H:%M")
            return dt.strftime("%d %B %Y")
        except ValueError:
            continue
    return date_str


def _format_price(event) -> str | None:
    if event.price_min is None and event.price_max is None:
        return None
    currency = event.currency or "EUR"
    symbol = "€" if currency.upper() == "EUR" else currency + " "
    if event.price_min is not None and event.price_max is not None and event.price_min != event.price_max:
        return f"{symbol}{event.price_min:.2f} – {symbol}{event.price_max:.2f}"
    price = event.price_min if event.price_min is not None else event.price_max
    return f"{symbol}{price:.2f}"


def build_embed(event, is_new: bool = True) -> dict:
    is_cancelled = (event.status or "").lower() in ("cancelled", "canceled")

    if is_cancelled:
        color = COLOR_CANCELLED
        title_prefix = "❌ Event geannuleerd"
    elif is_new:
        color = COLOR_NEW
        title_prefix = "🎸 Nieuwe touraankondiging"
    else:
        color = COLOR_CHANGED
        title_prefix = "🔄 Event bijgewerkt"

    fields = [
        {"name": "📍 Locatie", "value": f"{event.venue}, {event.city} ({event.country})", "inline": False},
        {"name": "📅 Datum", "value": _format_date(event.date), "inline": True},
    ]

    if event.support:
        fields.append({"name": "🎤 Support", "value": ", ".join(event.support), "inline": True})

    price = _format_price(event)
    if price:
        fields.append({"name": "💶 Tickets", "value": price, "inline": True})

    if event.status:
        fields.append({"name": "Status", "value": event.status, "inline": True})

    fields.append({"name": "Bron", "value": event.source, "inline": True})

    embed = {
        "title": f"{title_prefix}: {event.artist}",
        "url": event.url or None,
        "color": color,
        "fields": fields,
        "footer": {"text": f"Concert Notifier · {event.source}"},
    }
    if event.image_url:
        embed["thumbnail"] = {"url": event.image_url}

    return embed


def send_discord_notification(webhook_url: str, event, is_new: bool = True) -> bool:
    embed = build_embed(event, is_new=is_new)
    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException as exc:
        logger.error("Kon geen verbinding maken met Discord webhook: %s", exc)
        return False

    if resp.status_code == 429:
        retry_after = resp.json().get("retry_after", 1)
        logger.warning("Discord rate limit, wacht %ss en probeer opnieuw", retry_after)
        import time
        time.sleep(float(retry_after) + 0.5)
        return send_discord_notification(webhook_url, event, is_new=is_new)

    if resp.status_code not in (200, 204):
        logger.error("Discord webhook gaf status %s: %s", resp.status_code, resp.text[:300])
        return False

    logger.info("Discord melding verstuurd voor %s (%s)", event.artist, event.date)
    return True
