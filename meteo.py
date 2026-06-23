import requests
from datetime import datetime

LAT, LON = 48.8566, 2.3522
CITY_NAME = "Paris"

params = {
    "latitude": LAT,
    "longitude": LON,
    "hourly": "temperature_2m,precipitation",
    "timezone": "Europe/Paris",
    "forecast_days": 14,
    "temperature_unit": "celsius",
    "precipitation_unit": "mm",
}
resp = requests.get(
    "https://api.open-meteo.com/v1/forecast",
    params=params,
    timeout=30,
)
resp.raise_for_status()
data = resp.json()

hourly = data["hourly"]
times = hourly["time"]
temps = hourly["temperature_2m"]
precs = hourly.get("precipitation")

hours_all_raw = []
for t, temp, pr in zip(times, temps, precs):
    day_key = t[:10]
    hours_all_raw.append({"time": t, "date": day_key, "temp": temp, "precip": pr})

seen_dates = []
for h in hours_all_raw:
    if h["date"] not in seen_dates:
        seen_dates.append(h["date"])
selected_dates = seen_dates[:14]

hours_all = [h for h in hours_all_raw if h["date"] in selected_dates]

days = []
idx = 0
for dkey in selected_dates:
    day_hours = [h for h in hours_all if h["date"] == dkey]
    days.append({"date": dkey, "hours": day_hours, "startI": idx})
    idx += len(day_hours)

ALL_HOURS = []
for d in days:
    ALL_HOURS.extend(d["hours"])

HOUR_H = 2
LABEL_W = 96
PAD_L = 1
LEFT_SHIFT = 30
CURVE_LEFT = PAD_L + LEFT_SHIFT
CHART_W = 250
PAD_R = 28
CHART_SVG_W = CURVE_LEFT + CHART_W + PAD_R
TOTAL_H = len(ALL_HOURS) * HOUR_H


def y_of(i: int) -> float:
    return i * HOUR_H + 40


all_temps = [h["temp"] for h in ALL_HOURS]
g_min = min(all_temps)
g_max = max(all_temps)
g_range = (g_max - g_min) or 1


def x_of(t: float) -> float:
    return CURVE_LEFT + ((t - g_min) / g_range) * CHART_W


points = " ".join(f"{x_of(h['temp'])},{y_of(i)}" for i, h in enumerate(ALL_HOURS))

GRID_STROKE = "#d9d9d9"
GRID_STROKE_WIDTH = 1
GRID_HALO_COLOR = "#ffffff"
GRID_HALO_STROKE_WIDTH = 4


def parse_local_minutes(iso_time: str) -> int:
    dt = datetime.fromisoformat(iso_time)
    return dt.hour * 60 + dt.minute


grid_elements = []

for dayIdx in range(1, len(days)):
    y = y_of(days[dayIdx]["startI"])
    grid_elements.append(
        f'<line x1="{PAD_L}" y1="{y}" x2="{CURVE_LEFT + CHART_W}" y2="{y}" '
        f'stroke="{GRID_HALO_COLOR}" stroke-width="{GRID_HALO_STROKE_WIDTH}" />'
    )
    grid_elements.append(
        f'<line x1="{PAD_L}" y1="{y}" x2="{CURVE_LEFT + CHART_W}" y2="{y}" '
        f'stroke="{GRID_STROKE}" stroke-width="{GRID_STROKE_WIDTH}" />'
    )

mid_tick_len = 7
for day in days:
    day_hours = day["hours"]
    if not day_hours:
        continue

    target = 12 * 60
    best_i = min(
        range(len(day_hours)),
        key=lambda i: abs(parse_local_minutes(day_hours[i]["time"]) - target),
    )
    global_i = day["startI"] + best_i
    y = y_of(global_i)

    grid_elements.append(
        f'<line x1="{PAD_L}" y1="{y}" x2="{PAD_L + mid_tick_len}" y2="{y}" '
        f'stroke="{GRID_HALO_COLOR}" stroke-width="{GRID_HALO_STROKE_WIDTH}" />'
    )
    grid_elements.append(
        f'<line x1="{PAD_L}" y1="{y}" x2="{PAD_L + mid_tick_len}" y2="{y}" '
        f'stroke="{GRID_STROKE}" stroke-width="{GRID_STROKE_WIDTH}" />'
    )

grid_elements = "\n      ".join(grid_elements)

def rain_glyph(mm: float):
    if mm <= 0:
        return None
    if mm < 2:
        return "░░"
    if mm < 5:
        return "▒▒"
    return "▓▓"


def rain_color_opacity(mm: float):
    if mm < 2:
        return ("#2b6cb0", 0.75)
    if mm < 5:
        return ("#1a4fbf", 0.90)
    return ("#0b2f6a", 1.0)


RAIN_X = PAD_L

rain_elements = []
for i, h in enumerate(ALL_HOURS):
    mm = h["precip"] or 0.0
    g = rain_glyph(mm)
    if not g:
        continue
    color, op = rain_color_opacity(mm)
    rain_elements.append(
        f'<text x="{RAIN_X}" y="{y_of(i) + HOUR_H + 1}" text-anchor="start" '
        f'font-size="7" fill="{color}" opacity="{op}" font-family="monospace" '
        f'style="user-select:none;">{g}</text>'
    )

rain_elements = "\n      ".join(rain_elements)

annotation_elements = []
for day in days:
    day_hours = day["hours"]
    startI = day["startI"]

    minI = 0
    maxI = 0
    for i, h in enumerate(day_hours):
        if h["temp"] < day_hours[minI]["temp"]:
            minI = i
        if h["temp"] > day_hours[maxI]["temp"]:
            maxI = i

    tmax = day_hours[maxI]["temp"]
    tmin = day_hours[minI]["temp"]

    x_max = x_of(tmax) + 6
    y_max = y_of(startI + maxI) + 3
    x_min = x_of(tmin) - 6
    y_min = y_of(startI + minI) + 3

    annotation_elements.append(
        f"""<g>
  <text x="{x_max}" y="{y_max}" text-anchor="start"
        font-size="16" fill="#111" font-family="Georgia, serif"
        stroke="#fcfcfc" stroke-width="4" paint-order="stroke fill">
    {round(tmax)}°
  </text>
  <text x="{x_min}" y="{y_min}" text-anchor="end"
        font-size="16" fill="#111" font-family="Georgia, serif"
        stroke="#fcfcfc" stroke-width="4" paint-order="stroke fill">
    {round(tmin)}°
  </text>
</g>"""
    )

annotation_elements = "\n            ".join(annotation_elements)

DAYS_FR = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]


def fmt_day_fr(yyyy_mm_dd: str) -> str:
    d = datetime.fromisoformat(yyyy_mm_dd).date()
    js_get_day = (d.weekday() + 1) % 7
    return DAYS_FR[js_get_day]


def fmt_date_fr(yyyy_mm_dd: str) -> str:
    d = datetime.fromisoformat(yyyy_mm_dd).date()
    return f"{d.day} {MONTHS_FR[d.month - 1]}"


LABEL_TOP_SHIFT = 10

label_elements = []

label_elements.append(
    f"""<g>
      <text x="{LABEL_W - 6}" y="12" text-anchor="end"
        font-size="16" fill="#111" font-family="system-ui, sans-serif">

    {CITY_NAME}
  </text>
</g>"""
)

for dayIdx, day in enumerate(days):
    startI = day["startI"]
    is_today = dayIdx == 0

    day_top = "aujourd'hui" if is_today else fmt_day_fr(day["date"])
    day_bottom = fmt_date_fr(day["date"])

    label_elements.append(
        f"""<g>
  <text x="{LABEL_W - 6}" y="{y_of(startI) + LABEL_TOP_SHIFT + 5}" text-anchor="end"
        font-size="16" fill="#111" font-family="system-ui, sans-serif">
    {day_top}
  </text>
  <text x="{LABEL_W - 6}" y="{y_of(startI) + LABEL_TOP_SHIFT + 20}" text-anchor="end"
        font-size="12" fill="#111" font-family="system-ui, sans-serif">
    {day_bottom}
  </text>
</g>"""
    )

label_elements = "\n      ".join(label_elements)

html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      background: #fcfcfc;
      margin: 0;
      font-family: Georgia, serif;
      color: #111;
    }}
    .container {{ max-width: 420px; margin: 0 auto; padding: 36px 16px; }}
    .columns {{ display: flex; align-items: flex-start; gap: 12px; }}
    .columns svg {{ overflow: visible; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="columns">
      <svg width="{LABEL_W}" height="{TOTAL_H}" style="display:block; flex-shrink:0;">
        {label_elements}
      </svg>

      <svg width="{CHART_SVG_W}" height="{TOTAL_H}" style="display:block; flex-shrink:0;">
        {rain_elements}
        {grid_elements}
        <polyline points="{points}" fill="none" stroke="#111" stroke-width="1"/>
        {annotation_elements}
      </svg>
    </div>
  </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
