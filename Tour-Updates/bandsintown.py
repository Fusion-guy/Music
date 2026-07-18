"""
Bandsintown provider — OPTIONEEL.

LET OP: Bandsintown heeft de API sinds 2024 dichtgezet voor algemene
hobby-toepassingen. Een app_id wordt nu alleen nog uitgegeven aan de
artiest of diens management, gekoppeld aan dat ene artiest-profiel
(via Bandsintown for Artists -> Settings -> API Key). Er is dus geen
manier meer om als fan een key te krijgen die voor willekeurige
artiesten werkt.

Deze provider is er toch bij gezet zodat je hem kunt activeren áls je
ooit alsnog toegang krijgt (bijvoorbeeld een management-key voor één
specifieke band, of Bandsintown wijzigt het beleid weer). Standaard
staat hij UIT in config.yaml. Zonder geldige app_id geven calls
waarschijnlijk een 401/403 terug; dat wordt afgevangen en gelogd,
niet als crash.
"""

from __future__ import annotations

import logging
import time
from typing import List

import requests

from .base import Event, Provider

logger = logging.getLogger(__name__)

BASE_URL = "https://rest.bandsintown.com/artists/{artist}/events"


class BandsintownProvider(Provider):
    name = "Bandsintown"

    def __init__(self, app_id: str):
        self.app_id = app_id

    def fetch_events(self, artists: List[str], countries: List[str]) -> List[Event]:
        events: List[Event] = []
        for artist in artists:
            events.extend(self._fetch_for_artist(artist))
            time.sleep(0.25)
        # Bandsintown geeft geen land-filter mee in de events-call zelf,
        # dus filteren we hier client-side op de gewenste landcodes.
        return [e for e in events if e.country in countries]

    def _fetch_for_artist(self, artist: str) -> List[Event]:
        url = BASE_URL.format(artist=requests.utils.quote(artist))
        params = {"app_id": self.app_id, "date": "upcoming"}

        try:
            resp = requests.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            logger.error("Bandsintown request mislukt voor %s: %s", artist, exc)
            return []

        if resp.status_code in (401, 403):
            logger.warning(
                "Bandsintown weigert toegang voor %s (status %s) — "
                "waarschijnlijk geen geldige/algemene app_id meer beschikbaar.",
                artist, resp.status_code,
            )
            return []
        if resp.status_code != 200:
            logger.error("Bandsintown gaf status %s voor %s", resp.status_code, artist)
            return []

        try:
            raw_events = resp.json()
        except ValueError:
            logger.error("Bandsintown gaf geen geldige JSON terug voor %s", artist)
            return []

        if not isinstance(raw_events, list):
            return []

        results: List[Event] = []
        for raw in raw_events:
            parsed = self._parse_event(raw, artist)
            if parsed:
                results.append(parsed)
        return results

    def _parse_event(self, raw: dict, queried_artist: str) -> Event | None:
        try:
            venue = raw.get("venue", {})
            lineup = raw.get("lineup", [])
            support = [a for a in lineup if a.lower() != queried_artist.lower()]

            offers = raw.get("offers", [])
            url = offers[0]["url"] if offers else raw.get("url", "")

            return Event(
                artist=queried_artist,
                date=raw["datetime"],
                venue=venue.get("name", "Onbekende venue"),
                city=venue.get("city", "Onbekende stad"),
                country=venue.get("country", "??"),
                support=support,
                source=self.name,
                url=url,
                external_id=str(raw["id"]),
            )
        except (KeyError, TypeError) as exc:
            logger.warning("Kon Bandsintown event niet parsen: %s", exc)
            return None
