"""
Concert Notifier — pollt meerdere concert-APIs voor een lijst artiesten
en stuurt een Discord-melding zodra er een nieuw event verschijnt (of,
optioneel, wanneer een bestaand event van status/prijs verandert).

Gebruik:
    python main.py            # draait continu, pollt elke N minuten
    python main.py --once     # draait één keer en stopt (handig voor cron/testen)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from config import load_config
from notifier import send_discord_notification
from providers import BandsintownProvider, Event, TicketmasterProvider
from store import EventStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("concert-notifier")


def build_providers(cfg):
    providers = [
        TicketmasterProvider(
            api_key=cfg.ticketmaster_api_key,
            radius_km=cfg.radius_km,
            near_city=cfg.near_city,
        )
    ]
    if cfg.use_bandsintown:
        if not cfg.bandsintown_app_id:
            logger.warning(
                "use_bandsintown staat aan maar er is geen bandsintown_app_id ingesteld — "
                "Bandsintown wordt overgeslagen."
            )
        else:
            providers.append(BandsintownProvider(app_id=cfg.bandsintown_app_id))
    return providers


def run_once(cfg, providers, store: EventStore) -> None:
    all_events: list[Event] = []

    for provider in providers:
        try:
            events = provider.fetch_events(cfg.artists, cfg.countries)
            logger.info("%s: %d event(s) opgehaald", provider.name, len(events))
            all_events.extend(events)
        except Exception:
            # Eén kapotte provider mag de rest niet blokkeren.
            logger.exception("Onverwachte fout bij provider %s, ga verder met de rest", provider.name)

    new_count = 0
    changed_count = 0

    for event in all_events:
        key = event.dedup_key()

        if store.is_new(key):
            store.upsert(event)
            sent = send_discord_notification(cfg.discord_webhook_url, event, is_new=True)
            if sent:
                new_count += 1
            continue

        if cfg.notify_on_change and store.has_changed(key, event.status, event.price_min, event.price_max):
            store.upsert(event)
            sent = send_discord_notification(cfg.discord_webhook_url, event, is_new=False)
            if sent:
                changed_count += 1
        else:
            # Nog steeds "seen" bijwerken (last_seen_at) zonder melding.
            store.upsert(event)

    logger.info(
        "Ronde klaar: %d event(s) totaal bekeken, %d nieuw gemeld, %d wijziging(en) gemeld.",
        len(all_events), new_count, changed_count,
    )


def main():
    parser = argparse.ArgumentParser(description="Concert Notifier")
    parser.add_argument("--config", default=os.environ.get("CONFIG_PATH", "config.yaml"))
    parser.add_argument("--once", action="store_true", help="Draai één keer en stop (geen loop).")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
        sys.exit(1)

    os.makedirs(os.path.dirname(cfg.db_path) or ".", exist_ok=True)
    store = EventStore(cfg.db_path)

    if args.once:
        providers = build_providers(cfg)
        logger.info(
            "Concert Notifier gestart (eenmalig). Artiesten: %s | Landen: %s | Providers: %s",
            ", ".join(cfg.artists), ", ".join(cfg.countries),
            ", ".join(p.name for p in providers),
        )
        run_once(cfg, providers, store)
        return

    logger.info("Concert Notifier gestart in loop-modus (herleest config.yaml elke ronde).")

    while True:
        # Config bij elke ronde opnieuw inlezen. Zo kun je artiesten
        # toevoegen/verwijderen in config.yaml zonder de container te
        # hoeven herstarten of herbouwen — de wijziging wordt automatisch
        # meegenomen bij de eerstvolgende poll. Als het bestand tijdelijk
        # ongeldig is (bv. midden in het bewerken), blijft de vorige
        # geldige config gewoon actief in plaats van dat het script crasht.
        try:
            cfg = load_config(args.config)
        except (FileNotFoundError, ValueError) as exc:
            logger.error(
                "Kon config.yaml niet herladen (%s) — ga verder met de vorige geldige config.", exc
            )

        providers = build_providers(cfg)

        logger.info(
            "Ronde start. Artiesten: %s | Landen: %s | Providers: %s",
            ", ".join(cfg.artists), ", ".join(cfg.countries),
            ", ".join(p.name for p in providers),
        )

        try:
            run_once(cfg, providers, store)
        except Exception:
            logger.exception("Onverwachte fout in hoofdloop, probeer volgende ronde opnieuw.")

        time.sleep(cfg.poll_interval_minutes * 60)


if __name__ == "__main__":
    main()