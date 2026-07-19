"""
Gemeenschappelijke datastructuur en interface voor alle concert-providers.
Elke provider (Ticketmaster, Bandsintown, ...) geeft een lijst van
Event-objecten terug in dit gestandaardiseerde formaat, zodat main.py
ze allemaal op dezelfde manier kan verwerken.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Event:
    # Verplichte velden
    artist: str
    date: str  # ISO-formaat: "2026-11-12" of "2026-11-12T20:00:00"
    venue: str
    city: str
    country: str  # ISO country code, bv. "NL"
    source: str  # naam van de provider, bv. "Ticketmaster"
    url: str  # link naar de event-pagina
    external_id: str  # uniek ID zoals de provider het zelf geeft

    # Optionele verrijking
    support: List[str] = field(default_factory=list)
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None  # bv. "on sale", "cancelled", "postponed"
    image_url: Optional[str] = None

    def dedup_key(self) -> str:
        """Unieke sleutel die gebruikt wordt om te bepalen of we dit
        event al eerder gemeld hebben. Bevat de bron zodat verschillende
        providers elkaar niet per ongeluk overschrijven."""
        return f"{self.source}:{self.external_id}"


class Provider:
    """Basisklasse die elke concert-databron moet implementeren."""

    name: str = "base"

    def fetch_events(self, artists: List[str], countries: List[str]) -> List[Event]:
        """Haalt aankomende events op voor de gegeven artiesten,
        gefilterd op de gegeven landcodes. Moet een lijst van Event
        teruggeven (leeg is prima, exceptions worden door main.py
        afgevangen zodat één kapotte provider de rest niet blokkeert)."""
        raise NotImplementedError
