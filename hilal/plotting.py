"""Plot helpers for hilal chart rendering."""

import matplotlib.pyplot as plt
import numpy as np


def _wrap_az_deg(az):
    return (az + 360.0) % 360.0


def _small_circle_alt_for_az(alt0_deg, az0_deg, dist_deg, az_deg):
    """Altitude values of a constant angular-distance arc in local Alt/Az."""
    alt0 = np.deg2rad(alt0_deg)
    az0 = np.deg2rad(_wrap_az_deg(az0_deg))
    d = np.deg2rad(dist_deg)

    az = np.deg2rad(_wrap_az_deg(az_deg))
    delta = az - az0

    a = np.sin(alt0)
    b = np.cos(alt0) * np.cos(delta)
    c = np.cos(d)

    r = np.sqrt(a * a + b * b)
    ok = (r > 0) & (np.abs(c) <= r)

    alt_out = np.full_like(az, np.nan, dtype=float)
    alpha = np.arctan2(b, a)

    y = np.empty_like(az, dtype=float)
    y[ok] = np.arcsin(c / r[ok])

    x1 = y - alpha
    x2 = (np.pi - y) - alpha
    alt1 = np.rad2deg(x1)
    alt2 = np.rad2deg(x2)
    pick = np.where(np.nan_to_num(alt2, nan=-999) > np.nan_to_num(alt1, nan=-999), alt2, alt1)

    alt_out[ok] = pick[ok]
    return alt_out


def plot_hilal_chart_pretty(
    df_curve,
    sun_az_deg,
    sun_alt_deg,
    moon_az_deg,
    moon_alt_deg,
    alt_min_deg,
    elong_min_deg,
    elong_actual_deg,
    title,
    subtitle=None,
):
    center_az = float(sun_az_deg)
    span = 35.0
    az_min = center_az - span
    az_max = center_az + span
    wrap = (az_min < 0) or (az_max > 360)

    if not wrap:
        dfv = df_curve[(df_curve["az_moon"] >= az_min) & (df_curve["az_moon"] <= az_max)].copy()
        if dfv.empty:
            dfv = df_curve.copy()
    else:
        dfv = df_curve.copy()

    az_grid = np.linspace(az_min, az_max, 500) if not wrap else np.linspace(0, 360, 721)
    alt_el_min = _small_circle_alt_for_az(sun_alt_deg, sun_az_deg, elong_min_deg, az_grid)
    alt_el_act = _small_circle_alt_for_az(sun_alt_deg, sun_az_deg, elong_actual_deg, az_grid)

    y_candidates = list(dfv["alt_moon"].values) + [sun_alt_deg, moon_alt_deg, 0, alt_min_deg]
    if np.isfinite(alt_el_min).any():
        y_candidates += list(alt_el_min[np.isfinite(alt_el_min)])
    if np.isfinite(alt_el_act).any():
        y_candidates += list(alt_el_act[np.isfinite(alt_el_act)])
    y_min = max(-10, min(y_candidates) - 1.8)
    y_max = min(30, max(y_candidates) + 2.5)

    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    ax.axhline(0, linestyle="--", linewidth=1.5, color="gray", alpha=0.8, label="Ufuk (0°)")
    ax.axhline(
        alt_min_deg,
        linestyle="--",
        linewidth=2.2,
        color="red",
        alpha=0.9,
        label=f"{alt_min_deg:.1f}° Altitud Minimum",
    )

    ax.scatter([sun_az_deg], [sun_alt_deg], s=80, label="Matahari @ Maghrib", zorder=6)
    ax.scatter([moon_az_deg], [moon_alt_deg], s=80, label="Bulan @ Maghrib", zorder=7)

    right_side_free = True if wrap else (sun_az_deg - az_min) < (az_max - sun_az_deg)

    ax.plot([moon_az_deg, moon_az_deg], [0, moon_alt_deg], linewidth=3.0, alpha=0.85, label="Tinggi Hilal", zorder=4)
    ax.plot(
        [sun_az_deg, moon_az_deg],
        [sun_alt_deg, moon_alt_deg],
        linewidth=3.0,
        alpha=0.85,
        label="Jarak Lengkung",
        zorder=4,
    )  

    ax.plot(az_grid, alt_el_min, linestyle="--", linewidth=1.5, label=f"{elong_min_deg:.1f}° Had Elongasi", zorder=2)
    ax.plot(
        az_grid,
        alt_el_act,
        color="purple",
        linestyle=":",
        linewidth=2.0,
        label=f"Garis Elongasi (~= {elong_actual_deg:.2f}°)",
        zorder=2,
    )

    dx = 20 if right_side_free else -28
    dy = 4.2
    ax.annotate(
        f"Tinggi: {moon_alt_deg:.2f}°\nJarak Lengkung: {elong_actual_deg:.2f}°",
        xy=(moon_az_deg, moon_alt_deg),
        xytext=(moon_az_deg + dx, moon_alt_deg + dy),
        arrowprops=dict(arrowstyle="->", linewidth=1),
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", alpha=0.15),
        zorder=10,
    )

    ax.set_xlabel("Azimut (darjah)")
    ax.set_ylabel("Altitud (darjah)")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=22)
    if subtitle:
        ax.text(
            0.5,
            1.02,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=11,
            alpha=0.85,
        )

    ax.set_ylim(y_min, y_max)
    if not wrap:
        ax.set_xlim(az_min, az_max)
    ax.grid(True, linewidth=0.6, alpha=0.35)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=True)

    fig.tight_layout()
    return fig
