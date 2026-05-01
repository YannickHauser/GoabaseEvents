from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from folium import Map, Marker, Popup, Icon
from folium.plugins import MarkerCluster
from folium import Icon
from streamlit_folium import st_folium
import folium
from goabase_ingestion import fetch_goabase_events_switzerland
import streamlit.components.v1 as components
from branca.element import MacroElement
from jinja2 import Template


import html

CACHE_FILE = Path("events_cache.json")

st.set_page_config(
    page_title="Swiss Rave & Festival Map",
    page_icon="🎵",
    layout="wide",
)

def get_marker_color(event: dict[str, Any]) -> str:
    genres = [str(g).lower() for g in event.get("genres", [])]

    if any(g in genres for g in ["festival"]):
        return "purple"
    if any(g in genres for g in ["club"]):
        return "blue"
    if any(g in genres for g in ["open air", "outdoor"]):
        return "green"
    if any(g in genres for g in ["psytrance", "goa"]):
        return "darkpurple"
    if any(g in genres for g in ["techno"]):
        return "cadetblue"

    return "gray"


def add_genre_legend(map_object: Map) -> None:
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed;
        bottom: 35px;
        left: 35px;
        z-index: 999999;
        background-color: white;
        padding: 14px 16px;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        font-family: Arial, sans-serif;
        font-size: 13px;
        color: #111827;
        min-width: 175px;
        border: 1px solid #e5e7eb;
    ">
        <div style="font-weight: 700; margin-bottom: 8px; color: #111827;">
            Music style
        </div>

        <div style="margin-bottom: 5px; color: #111827;">
            <span style="color: purple; font-size: 18px;">●</span>
            Festival
        </div>

        <div style="margin-bottom: 5px; color: #111827;">
            <span style="color: blue; font-size: 18px;">●</span>
            Club
        </div>

        <div style="margin-bottom: 5px; color: #111827;">
            <span style="color: green; font-size: 18px;">●</span>
            Outdoor / Open Air
        </div>

        <div style="margin-bottom: 5px; color: #111827;">
            <span style="color: darkviolet; font-size: 18px;">●</span>
            Psytrance / Goa
        </div>

        <div style="margin-bottom: 5px; color: #111827;">
            <span style="color: cadetblue; font-size: 18px;">●</span>
            Techno
        </div>

        <div style="color: #111827;">
            <span style="color: gray; font-size: 18px;">●</span>
            Other
        </div>
    </div>
    {% endmacro %}
    """

    legend = MacroElement()
    legend._template = Template(legend_html)
    map_object.get_root().add_child(legend)


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }

        .hero {
            background: linear-gradient(135deg, #111827 0%, #312e81 60%, #7c3aed 100%);
            color: white;
            padding: 28px 32px;
            border-radius: 24px;
            margin-bottom: 24px;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.22);
        }

        .hero h1 {
            margin: 0;
            font-size: 28px;
            line-height: 1.1;
        }

        .hero p {
            margin-top: 10px;
            font-size: 15px;
            opacity: 0.9;
        }

        .event-card {
            background: white;
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .event-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #111827;
        }

        .event-meta {
            color: #475569;
            font-size: 14px;
            margin-bottom: 4px;
        }

        .genre-pill {
            display: inline-block;
            background: #ede9fe;
            color: #5b21b6;
            padding: 4px 9px;
            margin: 3px 4px 3px 0;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }

        .event-link {
            display: inline-block;
            margin-top: 8px;
            color: white !important;
            background: #111827;
            padding: 7px 11px;
            border-radius: 9px;
            text-decoration: none;
            font-weight: 600;
            font-size: 13px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_event_cards(events: list[dict[str, Any]], max_cards: int = 10) -> None:
    st.subheader("🎟️ Visible events")

    cards_html = ""

    for event in events[:max_cards]:
        title = html.escape(str(event.get("title") or "Untitled event"))
        city = html.escape(str(event.get("city") or "Unknown city"))
        venue = html.escape(str(event.get("venue_name") or "Venue not specified"))
        date_text = html.escape(str(format_datetime(event.get("start_datetime"))))
        genres = event.get("genres") or []
        event_url = event.get("event_url")
        image_url = event.get("image_url")

        genre_html = "".join(
            f'<span class="genre-pill">{html.escape(str(genre))}</span>'
            for genre in genres
        )

        image_html = ""
        if image_url:
            image_html = f"""
            <img src="{html.escape(str(image_url))}"
                 class="event-image">
            """

        link_html = ""
        if event_url:
            link_html = f"""
            <a class="event-link"
               href="{html.escape(str(event_url))}"
               target="_blank">
                Open on Goabase
            </a>
            """

        cards_html += f"""
        <div class="event-card">
            {image_html}
            <div class="event-title">{title}</div>
            <div class="event-meta">📅 {date_text}</div>
            <div class="event-meta">📍 {city} · {venue}</div>
            <div>{genre_html}</div>
            {link_html}
        </div>
        """

    html_doc = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: transparent;
                margin: 0;
                padding: 4px;
            }}

            .event-card {{
                background: white;
                border-radius: 18px;
                padding: 16px;
                margin-bottom: 16px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
                border: 1px solid rgba(148, 163, 184, 0.25);
            }}

            .event-image {{
                width: 100%;
                max-height: 180px;
                object-fit: cover;
                border-radius: 14px;
                margin-bottom: 12px;
            }}

            .event-title {{
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 6px;
                color: #111827;
            }}

            .event-meta {{
                color: #475569;
                font-size: 14px;
                margin-bottom: 4px;
            }}

            .genre-pill {{
                display: inline-block;
                background: #ede9fe;
                color: #5b21b6;
                padding: 4px 9px;
                margin: 3px 4px 3px 0;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 600;
            }}

            .event-link {{
                display: inline-block;
                margin-top: 8px;
                color: white;
                background: #111827;
                padding: 7px 11px;
                border-radius: 9px;
                text-decoration: none;
                font-weight: 600;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        {cards_html}
    </body>
    </html>
    """

    height = max(100, len(events[:max_cards]) * 360)
    components.html(html_doc, height=height, scrolling=True)

    if len(events) > max_cards:
        st.caption(f"Showing first {max_cards} of {len(events)} visible events.")


@st.cache_data(ttl=60 * 60 * 6)
def load_events(limit: int = 500) -> list[dict[str, Any]]:
    try:
        events = fetch_goabase_events_switzerland(limit=limit)

        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            json.dump(events, file, ensure_ascii=False, indent=2)

        return events

    except Exception as exc:
        st.warning(
            f"Could not fetch fresh Goabase data. Using local cache instead. Error: {exc}"
        )

        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as file:
                return json.load(file)

        raise RuntimeError(
            "Could not fetch Goabase data and no local cache file exists yet."
        ) from exc


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None

def get_event_date(event: dict[str, Any]) -> date | None:
    dt = parse_datetime(event.get("start_datetime"))
    if not dt:
        return None
    return dt.date()

def format_datetime(value: Any) -> str:
    dt = parse_datetime(value)
    if not dt:
        return "Unknown date"
    return dt.strftime("%d.%m.%Y %H:%M")


def event_has_coordinates(event: dict[str, Any]) -> bool:
    return event.get("lat") is not None and event.get("lon") is not None


def get_all_genres(events: list[dict[str, Any]]) -> list[str]:
    genres = set()

    for event in events:
        raw_genres = event.get("genres", [])

        if isinstance(raw_genres, list):
            for genre in raw_genres:
                if genre:
                    genres.add(str(genre).strip())

        elif isinstance(raw_genres, str):
            for genre in raw_genres.split(","):
                if genre.strip():
                    genres.add(genre.strip())

    return sorted(genres)

def filter_events(
    events: list[dict[str, Any]],
    selected_genres: list[str],
    search_text: str,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filtered = []

    for event in events:
        event_genres = event.get("genres", [])

        if selected_genres:
            if not any(genre in event_genres for genre in selected_genres):
                continue

        event_date = get_event_date(event)

        if date_from and event_date and event_date < date_from:
            continue

        if date_to and event_date and event_date > date_to:
            continue

        if date_from and date_to and event_date is None:
            continue

        if search_text:
            haystack = " ".join(
                str(event.get(key) or "")
                for key in ["title", "city", "venue_name", "description"]
            ).lower()

            if search_text.lower() not in haystack:
                continue

        filtered.append(event)

    return filtered


def build_popup_html(event: dict[str, Any]) -> str:
    title = html.escape(str(event.get("title") or "Untitled event"))
    city = html.escape(str(event.get("city") or "Unknown city"))
    venue = html.escape(str(event.get("venue_name") or "Venue not specified"))
    start = html.escape(format_datetime(event.get("start_datetime")))
    end = html.escape(format_datetime(event.get("end_datetime")))
    genres = html.escape(", ".join(event.get("genres") or []) or "Unknown style")

    description = str(event.get("description") or "").strip()
    if len(description) > 600:
        description = description[:600] + "..."
    description = html.escape(description)

    event_url = event.get("event_url")
    image_url = event.get("image_url")

    organizer = html.escape(str(event.get("organizer") or event.get("nameOrganizer") or ""))
    status = html.escape(str(event.get("status") or event.get("nameStatus") or ""))

    image_html = ""
    if image_url:
        image_html = f"""
        <img src="{html.escape(str(image_url))}"
             style="width:100%; max-height:160px; object-fit:cover;
                    border-radius:10px; margin-bottom:10px;">
        """

    organizer_html = ""
    if organizer:
        organizer_html = f"""
        <p style="margin:3px 0;"><b>Organizer:</b> {organizer}</p>
        """

    status_html = ""
    if status:
        status_html = f"""
        <p style="margin:3px 0;"><b>Status:</b> {status}</p>
        """

    description_html = ""
    if description:
        description_html = f"""
        <p style="margin-top:10px; line-height:1.35;">{description}</p>
        """

    link_html = ""
    if event_url:
        link_html = f"""
        <a href="{html.escape(str(event_url))}" target="_blank"
           style="
               display:inline-block;
               margin-top:10px;
               padding:7px 10px;
               background:#111827;
               color:white;
               text-decoration:none;
               border-radius:7px;
               font-weight:600;
           ">
           Open on Goabase
        </a>
        """

    return f"""
    <div style="
        width:310px;
        font-family:Arial, sans-serif;
        color:#111827;
    ">
        {image_html}

        <h3 style="
            margin:0 0 8px 0;
            font-size:17px;
            line-height:1.25;
        ">
            {title}
        </h3>

        <div style="
            background:#f3f4f6;
            padding:8px;
            border-radius:8px;
            margin-bottom:8px;
        ">
            <p style="margin:3px 0;"><b>Start:</b> {start}</p>
            <p style="margin:3px 0;"><b>End:</b> {end}</p>
            <p style="margin:3px 0;"><b>City:</b> {city}</p>
            <p style="margin:3px 0;"><b>Venue:</b> {venue}</p>
            <p style="margin:3px 0;"><b>Style:</b> {genres}</p>
            {organizer_html}
            {status_html}
        </div>

        {description_html}
        {link_html}
    </div>
    """



def build_map(events: list[dict[str, Any]], map_style: str) -> Map:
    swiss_center = [46.8182, 8.2275]

    m = Map(
        location=swiss_center,
        zoom_start=8,
        tiles=map_style,
    )


    marker_cluster = MarkerCluster().add_to(m)

    for event in events:
        if not event_has_coordinates(event):
            continue

        popup_html = build_popup_html(event)

        Marker(
            location=[event["lat"], event["lon"]],
            popup=Popup(popup_html, max_width=340),
            tooltip=event.get("title") or "Event",
            icon=Icon(color=get_marker_color(event), icon="music", prefix="fa"),
        ).add_to(marker_cluster)
    
    add_genre_legend(m)

    return m

def render_compact_event_cards(
    events: list[dict[str, Any]],
    max_cards: int = 4,
) -> None:
    for index, event in enumerate(events[:max_cards], start=1):
        title = event.get("title") or "Untitled event"
        city = event.get("city") or "Unknown city"
        venue = event.get("venue_name") or "Venue not specified"
        date_text = format_datetime(event.get("start_datetime"))
        genres = event.get("genres") or []
        event_url = event.get("event_url")
        image_url = event.get("image_url")

        st.markdown(f"### {index}. {title}")

        if image_url:
            st.image(image_url, width=260)

        st.caption(f"📅 {date_text}")
        st.caption(f"📍 {city} · {venue}")

        if genres:
            st.write(" ".join([f"`{genre}`" for genre in genres]))

        if event_url:
            st.markdown(f"[Open on Goabase]({event_url})")

        st.divider()

    if len(events) > max_cards:
        st.caption(f"Showing {max_cards} of {len(events)} visible events.")


def main() -> None:
    inject_custom_css()
    st.markdown(
        """
        <div class="hero">
            <h1>Swiss Rave & Festival Map</h1>
            <p>Discover Goabase events across Switzerland by location, date and music style.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Filters")

        map_style = st.selectbox(
            "Map style",
            options=[
                "CartoDB dark_matter",
                "CartoDB positron",
                "CartoDB voyager",
                "OpenStreetMap",
                "OpenTopoMap",
            ],
            index=0,
        )

        limit = st.slider(
            "Maximum events to fetch",
            min_value=10,
            max_value=500,
            value=200,
            step=10,
        )

        if st.button("Refresh Goabase data"):
            st.cache_data.clear()

            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()
        

    try:
        events = load_events(limit=limit)
    except Exception as exc:
        st.error(f"Could not load Goabase events: {exc}")
        st.stop()

    events_with_coordinates = [event for event in events if event_has_coordinates(event)]

    event_dates = [
    get_event_date(event)
    for event in events_with_coordinates
    if get_event_date(event) is not None
    ]

    if event_dates:
        min_event_date = min(event_dates)
        max_event_date = max(event_dates)
    else:
        min_event_date = date.today()
        max_event_date = date.today() + timedelta(days=90)

    all_genres = get_all_genres(events)

    with st.sidebar:
        selected_genres = st.multiselect(
            "Music style",
            options=all_genres,
            default=[],
        )

        search_text = st.text_input(
            "Search title, city, venue, description",
            value="",
        )

        date_preset = st.selectbox(
            "Date preset",
            options=[
                "All upcoming",
                "Today",
                "This weekend",
                "Next 7 days",
                "Next 30 days",
                "Custom range",
            ],
        )

        today = date.today()

        if date_preset == "Today":
            date_from = today
            date_to = today

        elif date_preset == "This weekend":
            days_until_saturday = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)
            date_from = saturday
            date_to = sunday

        elif date_preset == "Next 7 days":
            date_from = today
            date_to = today + timedelta(days=7)

        elif date_preset == "Next 30 days":
            date_from = today
            date_to = today + timedelta(days=30)

        elif date_preset == "Custom range":
            selected_range = st.date_input(
                "Date range",
                value=(min_event_date, max_event_date),
                min_value=min_event_date,
                max_value=max_event_date,
            )

            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                date_from, date_to = selected_range
            else:
                date_from = min_event_date
                date_to = max_event_date

        else:
            date_from = None
            date_to = None




    filtered_events = filter_events(
        events_with_coordinates,
        selected_genres=selected_genres,
        search_text=search_text,
        date_from=date_from,
        date_to=date_to,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Fetched events", len(events))
    col2.metric("Events with map location", len(events_with_coordinates))
    col3.metric("Visible events", len(filtered_events))

    if not filtered_events:
        st.warning("No events match the current filters.")
        st.stop()


    map_object = build_map(filtered_events, map_style=map_style)
    
    left_col, right_col = st.columns([2.4, 1])

    with left_col:
        st_folium(
            map_object,
            width=None,
            height=500,
        )

    with right_col:
        st.subheader("🔥 Featured events")
        render_compact_event_cards(filtered_events, max_cards=1)


    st_folium(
        map_object,
        width=None,
        height=700,
    )
    with st.expander("🎟️ Show visible events as cards", expanded=False):
        render_event_cards(filtered_events, max_cards=10)

    with st.expander("Event list"):
        table_data = []

        for event in filtered_events:
            table_data.append(
                {
                    "Title": event.get("title"),
                    "Date": format_datetime(event.get("start_datetime")),
                    "City": event.get("city"),
                    "Venue": event.get("venue_name"),
                    "Genres": ", ".join(event.get("genres") or []),
                    "URL": event.get("event_url"),
                }
            )
            

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()