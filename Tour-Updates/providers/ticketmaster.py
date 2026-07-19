"""
Ticketmaster Discovery API provider.

Gratis API key aanvragen op: https://developer.ticketmaster.com/
(account maken -> "My Apps" -> default app heeft al een Consumer Key,
dat IS je API key).

Documentatie: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

Dekking: NL zit in de landenlijst van de Discovery API, dus Nederlandse
en internationale shows in Nederland komen hierin voor.
"""

from __future__ import annotations

import logging
import time
from typing import List

import requests

from .base import Event, Provider

logger = logging.getLogger(__name__)

BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"


class TicketmasterProvider(Provider):
    name = "Ticketmaster"

    def __init__(self, api_key: str, radius_km: int = 0, near_city: str | None = None):
        self.api_key = api_key
        self.radius_km = radius_km
        self.near_city = near_city

    def fetch_events(self, artists: List[str], countries: List[str]) -> List[Event]:
        events: List[Event] = []
        for artist in artists:
            for country in countries:
                events.extend(self._fetch_for_artist(artist, country))
                # Wees aardig voor de rate limit (5 req/s default).
                time.sleep(0.25)
        return events

    def _fetch_for_artist(self, artist: str, country: str) -> List[Event]:
        params = {
            "apikey": self.api_key,
            "keyword": artist,
            "countryCode": country,
            "classificationName": "music",
            "size": 50,
            "sort": "date,asc",
        }
        if self.near_city:
            params["city"] = self.near_city
        if self.radius_km:
            params["radius"] = self.radius_km
            params["unit"] = "km"

        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
        except requests.RequestException as exc:
            logger.error("Ticketmaster request mislukt voor %s (%s): %s", artist, country, exc)
            return []

        if resp.status_code == 429:
            logger.warning("Ticketmaster rate limit bereikt, sla deze ronde over voor %s", artist)
            return []
        if resp.status_code != 200:
            logger.error(
                "Ticketmaster gaf status %s voor %s (%s): %s",
                resp.status_code, artist, country, resp.text[:300],
            )
            return []

        data = resp.json()
        raw_events = data.get("_embedded", {}).get("events", [])

        results: List[Event] = []
        for raw in raw_events:
            parsed = self._parse_event(raw, artist)
            if parsed:
                results.append(parsed)
        return results

    def _parse_event(self, raw: dict, queried_artist: str) -> Event | None:
        try:
            event_id = raw["id"]
            name = raw.get("name", queried_artist)

            dates = raw.get("dates", {}).get("start", {})
            date_str = dates.get("dateTime") or dates.get("localDate")
            if not date_str:
                return None

            venues = raw.get("_embedded", {}).get("venues", [{}])
            venue = venues[0] if venues else {}
            venue_name = venue.get("name", "Onbekende venue")
            city = venue.get("city", {}).get("name", "Onbekende stad")
            country = venue.get("country", {}).get("countryCode", "??")

            # Voorprogramma / andere line-up leden onder de headliner.
            attractions = raw.get("_embedded", {}).get("attractions", [])
            support = [
                a["name"] for a in attractions
                if a.get("name") and a["name"].lower() != queried_artist.lower()
            ]

            price_min = price_max = currency = None
            price_ranges = raw.get("priceRanges")
            if price_ranges:
                pr = price_ranges[0]
                price_min = pr.get("min")
                price_max = pr.get("max")
                currency = pr.get("currency")

            status = raw.get("dates", {}).get("status", {}).get("code")

            images = raw.get("images", [])
            image_url = images[0]["url"] if images else None

            return Event(
                artist=queried_artist,
                date=date_str,
                venue=venue_name,
                city=city,
                country=country,
                support=support,
                price_min=price_min,
                price_max=price_max,
                currency=currency,
                status=status,
                image_url=image_url,
                source=self.name,
                url=raw.get("url", ""),
                external_id=event_id,
            )
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Kon Ticketmaster event niet parsen: %s (%s)", exc, raw.get("id"))
            return None
