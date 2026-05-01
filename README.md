# Swiss Rave & Festival Map

An interactive Streamlit app that displays Goabase events in Switzerland on a map.  
Users can explore upcoming raves, festivals, club nights, and open-air events, filter them by music style and date, and click map markers to view event details.

## Features

- Interactive Switzerland map
- Event markers from Goabase
- Clickable event popups
- Music-style filtering
- Date filtering
- Search by title, city, venue, or description
- Local JSON cache so the app still works if the Goabase API is temporarily unavailable
- Optional map style selector
- Featured events panel
- Genre-colored map markers

## Data Source

The app currently uses the Goabase party API:

```text
https://www.goabase.net/api/party/json/?country=CH
