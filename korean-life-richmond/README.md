# Korean Life in Richmond — map

Self-contained interactive map (`index.html`, no external dependencies besides Google Fonts) of Korean churches, grocery stores, academies and hospitals in the Richmond, VA metro. Built for the YouTube video "A Guide to Korean Life in Richmond".

- `data/places.json` — curated places (edit here, then rebuild)
- `data/places_geo.json` — the same list with coordinates from Overture Maps address points
- `tools/fetch.py` — pulls Overture Maps layers (roads, water, parks, counties, places, addresses) for the Richmond bbox from S3
- `tools/geocode.py` — matches each address to an Overture address point
- `tools/build_layers.py` — projects and simplifies the base map into SVG paths
- `tools/build_html.py` + `tools/template.html` — assembles `index.html`

Rebuild: `python3 tools/fetch.py <divisions|water|roads|places|addresses>` for each layer, then `geocode.py`, `build_layers.py`, `build_html.py` (needs `pyarrow`, `shapely`).

Keyboard: `P` presentation mode, `R` reset view, `1`–`4` toggle categories, `+`/`-` zoom, `Esc` close card.

## Hosting and analytics

`site/index.html` is the standalone build (full HTML document) for hosting on Vercel, Netlify or GitHub Pages. Put your Google Analytics 4 measurement ID in `data/site.json` (`"ga4_measurement_id": "G-XXXXXXXXXX"`) and run `python3 tools/build_html.py` to bake the gtag snippet in. The page sends `select_place`, `area_view` and `present_mode` events, and GA4 reads the `utm_*` parameters from the link automatically.
