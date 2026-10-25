"""Weather warnings (Met Éireann, MeteoAlarm, US NWS) as a binary sensor.

Feed parsing and matching live here, free of Home Assistant imports, so they can be tested standalone.
Every source is normalised to: {level, type, regions, onset, expiry, headline}.
"""
from datetime import datetime
import math

DOMAIN = "storm_warnings"

# Met Éireann county codes: (name, approximate centre lat, lon)
COUNTIES = {
    "EI01": ("Carlow", 52.72, -6.84), "EI02": ("Cavan", 53.99, -7.36), "EI03": ("Clare", 52.90, -9.00),
    "EI04": ("Cork", 51.95, -8.75), "EI06": ("Donegal", 54.90, -8.00), "EI07": ("Dublin", 53.35, -6.27),
    "EI10": ("Galway", 53.35, -8.90), "EI11": ("Kerry", 52.10, -9.65), "EI12": ("Kildare", 53.20, -6.80),
    "EI13": ("Kilkenny", 52.58, -7.22), "EI14": ("Leitrim", 54.10, -8.00), "EI15": ("Laois", 53.00, -7.40),
    "EI16": ("Limerick", 52.50, -8.75), "EI18": ("Longford", 53.73, -7.70), "EI19": ("Louth", 53.92, -6.48),
    "EI20": ("Mayo", 53.90, -9.30), "EI21": ("Meath", 53.62, -6.70), "EI22": ("Monaghan", 54.15, -6.95),
    "EI23": ("Offaly", 53.20, -7.60), "EI24": ("Roscommon", 53.70, -8.20), "EI25": ("Sligo", 54.15, -8.60),
    "EI26": ("Tipperary", 52.65, -7.90), "EI27": ("Waterford", 52.20, -7.60), "EI29": ("Westmeath", 53.55, -7.45),
    "EI30": ("Wexford", 52.45, -6.60), "EI31": ("Wicklow", 53.00, -6.40),
}


def nearest_county(lat, lon):
    """Best-guess county code for a point in Ireland, or None outside it. Only used as a setup default."""
    # ponytail: nearest county centre, can pick a neighbour near borders; use county polygons if that matters
    if not (51.3 <= lat <= 55.5 and -10.7 <= lon <= -5.9):
        return None
    k = math.cos(math.radians(lat))
    return min(COUNTIES, key=lambda c: (COUNTIES[c][1] - lat) ** 2 + ((COUNTIES[c][2] - lon) * k) ** 2)

LEVELS = ["yellow", "orange", "red"]
CAP_LEVELS = {"Moderate": "yellow", "Severe": "orange", "Extreme": "red"}


def parse_met_eireann(data):
    return data  # already in the normalised shape


def parse_meteoalarm(data):
    out = []
    for w in data["warnings"]:
        info = w["alert"]["info"][0]  # one entry per language, same content
        params = {p["valueName"]: p["value"] for p in info.get("parameter", [])}
        out.append({
            "level": params.get("awareness_level", "; ;").split("; ")[1],  # "2; yellow; Moderate"
            "type": params.get("awareness_type", "; ").split("; ")[1],  # "1; Wind"
            "regions": [g["value"] for a in info.get("area", []) for g in a.get("geocode", [])],
            "onset": info.get("onset") or info["effective"],
            "expiry": info["expires"],
            "headline": info.get("headline", ""),
        })
    return out


def parse_nws(data):
    out = []
    for f in data["features"]:
        p = f["properties"]
        out.append({
            "level": CAP_LEVELS.get(p["severity"]),
            "type": p["event"],
            "regions": [],  # already filtered by the point query
            "onset": p.get("onset") or p["effective"],
            "expiry": p.get("ends") or p["expires"],  # "expires" is when the bulletin is reissued, not the event end
            "headline": p.get("headline") or p["event"],
        })
    return out


PARSERS = {"met_eireann": parse_met_eireann, "meteoalarm": parse_meteoalarm, "nws": parse_nws}


def feed_url(config):
    if config["source"] == "met_eireann":
        return "https://www.met.ie/Open_Data/json/warning_IRELAND.json"
    if config["source"] == "meteoalarm":
        return f"https://feeds.meteoalarm.org/api/v1/warnings/feeds-{config['country']}"
    return f"https://api.weather.gov/alerts/active?point={config['latitude']:.4f},{config['longitude']:.4f}"


def matching(warnings, regions, now, lead, min_level="yellow", types=()):
    """Warnings for our regions, at or above min_level, that are active or start within `lead`."""
    out = []
    for w in warnings:
        if w.get("level") not in LEVELS or LEVELS.index(w["level"]) < LEVELS.index(min_level):
            continue
        if types and not any(t in w.get("type", "").lower() for t in types):
            continue
        # ponytail: empty regions treated as nationwide; unverified for met.ie, check a national warning's JSON when one is issued
        if w.get("regions") and not set(w["regions"]) & set(regions):
            continue
        onset = datetime.fromisoformat(w["onset"])
        expiry = datetime.fromisoformat(w["expiry"])
        if onset - lead <= now < expiry:
            out.append(w)
    return out


async def async_setup_entry(hass, entry):
    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, ["binary_sensor"])


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
