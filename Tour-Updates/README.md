# Concert Notifier

Pollt periodiek de Ticketmaster Discovery API voor een lijst artiesten,
filtert op land/regio (standaard NL), en stuurt een nette Discord-embed
zodra er een **nieuwe** tourdatum verschijnt — met band, datum, venue,
voorprogramma en ticketprijzen. Voorkomt dubbele meldingen via een
lokale SQLite-database, en kan optioneel ook melden als een bestaand
event van status verandert (bv. tickets net live, of geannuleerd).

## Waarom alleen Ticketmaster als "echte" bron?

Er is bewust gekozen voor één betrouwbare bron in plaats van meerdere
half-werkende bronnen:

- **Ticketmaster Discovery API** — gratis, zelf een key aanmaken, dekt
  Nederland en de meeste omliggende landen. Dit is de hoofd-bron.
- **Bandsintown** — zit erbij (`providers/bandsintown.py`), maar staat
  **standaard uit**. Bandsintown geeft tegenwoordig alleen nog
  app_id's uit aan artiesten/hun management voor hun eigen profiel,
  niet meer aan fans voor willekeurige artiesten. Mocht dat ooit
  veranderen (of heb je zelf al een geldige key), zet 'm dan aan in
  `config.yaml`.
- **Songkick** — is niet geïmplementeerd. Songkick accepteert al een
  tijd geen nieuwe hobby/student-aanvragen meer voor API-toegang;
  alleen nog betaalde partnerships.

De architectuur (`providers/base.py`) is bewust generiek opgezet zodat
je zelf eenvoudig een nieuwe provider kunt toevoegen (bijvoorbeeld een
scraper voor een specifieke venue-website) — implementeer gewoon
`fetch_events()` en geef `Event`-objecten terug.

## Installatie

### 1. API-key en webhook regelen

- **Ticketmaster**: maak een gratis account op
  https://developer.ticketmaster.com/, ga naar "My Apps" — je Consumer
  Key is je API key.
- **Discord webhook**: in je Discord-server -> Server Settings ->
  Integrations -> Webhooks -> New Webhook -> kopieer de URL.

### 2. Config instellen

```bash
cp config.example.yaml config.yaml
```

Vul in `config.yaml` je artiesten, `ticketmaster_api_key` en
`discord_webhook_url` in.

### 3. Draaien met Docker (aanbevolen)

```bash
docker compose up -d --build
docker compose logs -f
```

De container blijft draaien en pollt elke `poll_interval_minutes`
(standaard 30) automatisch. De SQLite-database staat in `./data/`, dus
die overleeft een herstart van de container.

### 4. Of lokaal draaien zonder Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Voor een eenmalige testrun (bv. om te checken of alles werkt, of om
via een externe cronjob te draaien in plaats van de ingebouwde loop):

```bash
python main.py --once
```

## Configuratie-opties (`config.yaml`)

| Optie | Omschrijving |
|---|---|
| `artists` | Lijst met bandnamen om te volgen |
| `countries` | ISO-landcodes om op te filteren, bv. `["NL", "BE"]` |
| `near_city` / `radius_km` | Optioneel filteren op afstand tot een stad |
| `poll_interval_minutes` | Hoe vaak gepolld wordt |
| `notify_on_change` | Ook melden bij prijs/status-wijziging van een al bekend event |
| `discord_webhook_url` | Discord webhook (kan ook via env var `DISCORD_WEBHOOK_URL`) |
| `ticketmaster_api_key` | Ticketmaster key (kan ook via env var `TICKETMASTER_API_KEY`) |
| `use_bandsintown` / `bandsintown_app_id` | Zie uitleg hierboven |

## Uitbreiden

Nieuwe provider toevoegen:

1. Maak `providers/mijn_bron.py` met een klasse die van `Provider`
   erft en `fetch_events(artists, countries) -> list[Event]`
   implementeert.
2. Registreer 'm in `providers/__init__.py` en in `build_providers()`
   in `main.py`.

Dat is alles — de rest (dedup, Discord-formatting, scheduling) werkt
automatisch mee omdat het allemaal op het gestandaardiseerde
`Event`-object draait.

## Rate limits

Ticketmaster: standaard 5000 calls/dag en 5 req/s per key. Bij bv. 5
artiesten x 1 land x elke 30 min = 240 calls/dag, dus ruim binnen de
limiet. Bij veel artiesten/landen kun je `poll_interval_minutes`
verhogen om binnen de limiet te blijven.
