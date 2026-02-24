"""Astronomical computations for hilal visibility."""

import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from skyfield import almanac
from skyfield.api import wgs84


def rad2deg(x: float) -> float:
    return x * 180.0 / math.pi


def angular_separation_deg(vec1, vec2) -> float:
    """Angular separation between two Skyfield vectors in degrees."""
    a = vec1.au
    b = vec2.au
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    cosang = max(-1.0, min(1.0, dot / (na * nb)))
    return rad2deg(math.acos(cosang))


def to_utc_window_for_local_date(on_date: date, tz_offset_hours: int):
    """Build UTC datetime start/end for a local date + fixed UTC offset."""
    local_start = datetime(on_date.year, on_date.month, on_date.day, 0, 0, 0)
    local_end = local_start + timedelta(days=1)
    offset = timedelta(hours=tz_offset_hours)
    utc_start = (local_start - offset).replace(tzinfo=timezone.utc)
    utc_end = (local_end - offset).replace(tzinfo=timezone.utc)
    return utc_start, utc_end


def find_sunset_time(ts, eph, lat: float, lon: float, on_date: date, tz_offset_hours: int):
    """Find local sunset time. Returns (t_sunset, sunset_local_dt) or (None, None)."""
    loc = wgs84.latlon(lat, lon)
    utc_start, utc_end = to_utc_window_for_local_date(on_date, tz_offset_hours)
    t0 = ts.from_datetime(utc_start)
    t1 = ts.from_datetime(utc_end)

    times, events = almanac.find_discrete(t0, t1, almanac.sunrise_sunset(eph, loc))
    sunset_idx = np.where(events == 0)[0]
    if len(sunset_idx) == 0:
        return None, None

    t_sunset = times[sunset_idx[0]]
    sunset_utc = t_sunset.utc_datetime().replace(tzinfo=timezone.utc)
    sunset_local = (sunset_utc + timedelta(hours=tz_offset_hours)).replace(tzinfo=None)
    return t_sunset, sunset_local


def find_moonset_time(ts, eph, lat: float, lon: float, on_date: date, tz_offset_hours: int):
    """Find local moonset time. Returns (t_moonset, moonset_local_dt) or (None, None)."""
    loc = wgs84.latlon(lat, lon)
    utc_start, utc_end = to_utc_window_for_local_date(on_date, tz_offset_hours)
    t0 = ts.from_datetime(utc_start)
    t1 = ts.from_datetime(utc_end)

    f = almanac.risings_and_settings(eph, eph["moon"], loc)
    times, events = almanac.find_discrete(t0, t1, f)
    moonset_idx = np.where(events == 0)[0]
    if len(moonset_idx) == 0:
        return None, None

    t_moonset = times[moonset_idx[0]]
    set_utc = t_moonset.utc_datetime().replace(tzinfo=timezone.utc)
    set_local = (set_utc + timedelta(hours=tz_offset_hours)).replace(tzinfo=None)
    return t_moonset, set_local


def compute_params_at(eph, lat: float, lon: float, t):
    """Compute sun/moon alt-az and sun-moon elongation at time t."""
    observer = eph["earth"] + wgs84.latlon(lat, lon)

    ast_moon = observer.at(t).observe(eph["moon"]).apparent()
    ast_sun = observer.at(t).observe(eph["sun"]).apparent()

    alt_m, az_m, _ = ast_moon.altaz()
    alt_s, az_s, _ = ast_sun.altaz()
    elong = angular_separation_deg(ast_moon.position, ast_sun.position)

    return {
        "moon_alt_deg": float(alt_m.degrees),
        "moon_az_deg": float(az_m.degrees),
        "sun_alt_deg": float(alt_s.degrees),
        "sun_az_deg": float(az_s.degrees),
        "elong_deg": float(elong),
    }


def sample_moon_track(ts, eph, lat: float, lon: float, t_center, minutes_before=60, minutes_after=20, step_seconds=30):
    """Sample moon/sun alt-az around maghrib for charting."""
    start = t_center - minutes_before / (24 * 60)
    end = t_center + minutes_after / (24 * 60)
    total_seconds = int((minutes_before + minutes_after) * 60)
    steps = max(2, total_seconds // step_seconds)
    t_grid = ts.tt_jd(np.linspace(start.tt, end.tt, steps))

    observer = eph["earth"] + wgs84.latlon(lat, lon)
    ast_moon = observer.at(t_grid).observe(eph["moon"]).apparent()
    ast_sun = observer.at(t_grid).observe(eph["sun"]).apparent()

    alt_m, az_m, _ = ast_moon.altaz()
    alt_s, az_s, _ = ast_sun.altaz()
    return pd.DataFrame(
        {
            "az_moon": az_m.degrees,
            "alt_moon": alt_m.degrees,
            "az_sun": az_s.degrees,
            "alt_sun": alt_s.degrees,
        }
    )


def evaluate_one_location(
    ts,
    eph,
    lat: float,
    lon: float,
    on_date: date,
    tz_offset: int,
    alt_min: float,
    elong_min: float,
    include_moonset: bool = True,
):
    """Evaluate one location against MABIMS criteria at sunset."""
    t_sunset, sunset_local = find_sunset_time(ts, eph, lat, lon, on_date, tz_offset)
    if t_sunset is None:
        return None

    vals = compute_params_at(eph, lat, lon, t_sunset)
    moon_alt = vals["moon_alt_deg"]
    elong = vals["elong_deg"]
    passed = (moon_alt >= alt_min) and (elong >= elong_min)

    moonset_local = None
    lag_minutes = None
    if include_moonset:
        _, moonset_local = find_moonset_time(ts, eph, lat, lon, on_date, tz_offset)
        if moonset_local is not None:
            lag_minutes = (moonset_local - sunset_local).total_seconds() / 60.0

    return {
        "sunset_local": sunset_local,
        "moon_alt_deg": moon_alt,
        "moon_az_deg": vals["moon_az_deg"],
        "sun_alt_deg": vals["sun_alt_deg"],
        "sun_az_deg": vals["sun_az_deg"],
        "elong_deg": elong,
        "passed": passed,
        "moonset_local": moonset_local,
        "lag_minutes": lag_minutes,
        "t_sunset": t_sunset,
    }

