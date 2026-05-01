from __future__ import annotations

import argparse
import json
import re
from typing import Any
from urllib.parse import urljoin

import requests


GOABASE_BASE_URL = "https://www.goabase.net"
GOABASE_API_URL = "https://www.goabase.net/api/party/json/"


GENRE_MAP = {
    "psychedelic trance": "psytrance",
    "goa": "psytrance",
    "goa trance": "psytrance",
    "melodic techno": "techno",
    "hard techno": "techno",
    "dnb": "drum & bass",
    "drum and bass": "drum & bass",
}


# ------------------------
# Helpers
# ------------------------

def normalize_genre(raw_genre: str) -> str:
    value = raw_genre.strip().lower()
    return GENRE_MAP.get(value, value)


def split_genres(raw: Any) -> list[str]:
    if raw is None:
        return []

    if isinstance(raw, list):
        candidates = raw
    else:
        candidates = re.split(r"[,;/|]+", str(raw))

    genres = []
    for item in candidates:
        genre = normalize_genre(str(item))
        if genre and genre not in genres:
            genres.append(genre)

    return genres


def first_present(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return default


def absolutize_url(url: Any) -> str | None:
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(GOABASE_BASE_URL, url)


# ------------------------
# Normalization
# ------------------------

def normalize_goabase_event(raw: dict[str, Any]) -> dict[str, Any]:
    source_event_id = str(first_present(raw, ["id"], ""))

    title = first_present(raw, ["nameParty", "name", "partyName", "title"], "")

    city = first_present(
        raw,
        ["nameTown", "locationCity", "city", "addressLocality"],
    )

    venue_name = first_present(
        raw,
        ["locationName", "venueName", "placeName", "location", "nameLocation"],
    )

    lat = first_present(raw, ["geoLat", "geoLatitude", "latitude", "lat"])
    lon = first_present(raw, ["geoLon", "geoLongitude", "longitude", "lon", "lng"])

    try:
        lat = float(lat) if lat is not None else None
    except (TypeError, ValueError):
        lat = None

    try:
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        lon = None

    raw_genres = first_present(
        raw,
        [
            "nameType",
            "music",
            "musicStyle",
            "musicStyles",
            "style",
            "styles",
            "genre",
            "genres",
            "tags",
            "keywords",
            "category",
            "categories",
        ],
    )

    print("Raw genre field:", raw_genres)

    event_url = absolutize_url(
        first_present(raw, ["urlPartyHtml", "url", "eventUrl", "partyUrl", "link"])
    )

    image_url = absolutize_url(
        first_present(
            raw,
            [
                "urlImageLarge",
                "urlImageFull",
                "urlImageMedium",
                "urlImageSmall",
                "image",
                "imageUrl",
                "flyer",
                "flyerUrl",
                "thumbnailUrl",
            ],
        )
    )

    return {
    "title": title,
    "source": "goabase",
    "source_event_id": source_event_id,
    "start_datetime": first_present(raw, ["dateStart", "startDate", "start_datetime", "start"]),
    "end_datetime": first_present(raw, ["dateEnd", "endDate", "end_datetime", "end"]),
    "venue_name": venue_name,
    "city": city,
    "country": "CH",
    "lat": lat,
    "lon": lon,
    "genres": split_genres(raw_genres),
    "description": first_present(raw, ["description", "info", "text", "about"], ""),
    "ticket_url": None,
    "event_url": event_url,
    "image_url": image_url,
    "organizer": first_present(raw, ["nameOrganizer", "organizer"], ""),
    "status": first_present(raw, ["nameStatus", "status"], ""),
    }

'''
    return {
        "title": title,
        "source": "goabase",
        "source_event_id": source_event_id,
        "start_datetime": first_present(
            raw,
            ["dateStart", "startDate", "start_datetime", "start"],
        ),
        "end_datetime": first_present(
            raw,
            ["dateEnd", "endDate", "end_datetime", "end"],
        ),
        "venue_name": venue_name,
        "city": city,
        "country": "CH",
        "lat": lat,
        "lon": lon,
        "genres": split_genres(raw_genres),
        "description": first_present(
            raw,
            ["description", "info", "text", "about"],
            "",
        ),
        "ticket_url": None,
        "event_url": event_url,
        "image_url": image_url,
    }

'''

# ------------------------
# Extraction logic (FIXED)
# ------------------------

def extract_event_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected payload type: {type(payload)}")

    print("Goabase top-level keys:", list(payload.keys()))

    for key in [
        "partyList",
        "parties",
        "party",
        "events",
        "event",
        "data",
        "items",
        "results",
    ]:
        value = payload.get(key)
        if isinstance(value, list):
            return value

    for key, value in payload.items():
        if isinstance(value, list) and all(isinstance(x, dict) for x in value):
            print(f"Using fallback key: {key}")
            return value

    debug_preview = json.dumps(payload, ensure_ascii=False, indent=2)[:2000]
    raise ValueError(
        "Could not find event list.\n"
        f"Payload preview:\n{debug_preview}"
    )


# ------------------------
# Fetch
# ------------------------

def fetch_goabase_events_switzerland(
    limit: int = 100,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    params = {
        "country": "CH",
        "limit": limit,
    }

    response = requests.get(
        GOABASE_API_URL,
        params=params,
        timeout=timeout,
        headers={
            "Accept": "application/json",
            "User-Agent": "swiss-event-map/0.1",
        },
    )

    print("Request URL:", response.url)
    print("Status:", response.status_code)

    response.raise_for_status()

    payload = response.json()

    raw_events = extract_event_list(payload)

    return [normalize_goabase_event(e) for e in raw_events]


# ------------------------
# CLI
# ------------------------

def save_events_json(events: list[dict[str, Any]], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", default="goabase_ch_events.json")
    args = parser.parse_args()

    events = fetch_goabase_events_switzerland(limit=args.limit)
    save_events_json(events, args.output)

    print(f"Saved {len(events)} events → {args.output}")


if __name__ == "__main__":
    main()