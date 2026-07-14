"""Plot helpers for hilal chart rendering."""

import matplotlib.pyplot as plt
import numpy as np


MYDS_LIGHT = {
    "primary": "#2563EB",
    "danger": "#B91C1C",
    "success": "#15803D",
    "warning": "#A16207",
    "text": "#18181B",
    "text_muted": "#6B6B74",
    "border": "#E4E4E7",
    "washed": "#F4F4F5",
    "white": "#FFFFFF",
}

MYDS_DARK = {
    "primary": "#6394FF",
    "danger": "#F87171",
    "success": "#22C55E",
    "warning": "#EAB308",
    "text": "#FFFFFF",
    "text_muted": "#A1A1AA",
    "border": "#3F3F46",
    "washed": "#27272A",
    "white": "#18181B",
}


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
    dark_mode=False,
):
    palette = MYDS_DARK if dark_mode else MYDS_LIGHT
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

    fig = plt.figure(figsize=(12, 6), facecolor=palette["white"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(palette["white"])
    ax.axhline(
        0,
        linestyle="--",
        linewidth=1.5,
        color=palette["text_muted"],
        alpha=0.9,
        label="Ufuk (0°)",
    )
    ax.axhline(
        alt_min_deg,
        linestyle="--",
        linewidth=2.2,
        color=palette["danger"],
        alpha=0.9,
        label=f"Had altitud {alt_min_deg:.1f}°",
    )

    ax.scatter(
        [sun_az_deg],
        [sun_alt_deg],
        s=80,
        color=palette["warning"],
        label="Matahari ketika terbenam",
        zorder=6,
    )
    ax.scatter(
        [moon_az_deg],
        [moon_alt_deg],
        s=80,
        color=palette["primary"],
        label="Bulan ketika matahari terbenam",
        zorder=7,
    )

    right_side_free = True if wrap else (sun_az_deg - az_min) < (az_max - sun_az_deg)

    ax.plot(
        [moon_az_deg, moon_az_deg],
        [0, moon_alt_deg],
        linewidth=3.0,
        color=palette["primary"],
        alpha=0.85,
        label="Tinggi hilal",
        zorder=4,
    )
    ax.plot(
        [sun_az_deg, moon_az_deg],
        [sun_alt_deg, moon_alt_deg],
        linewidth=3.0,
        color=palette["success"],
        alpha=0.85,
        label="Jarak lengkung",
        zorder=4,
    )

    ax.plot(
        az_grid,
        alt_el_min,
        color=palette["danger"],
        linestyle="--",
        linewidth=1.5,
        label=f"Had elongasi {elong_min_deg:.1f}°",
        zorder=2,
    )
    ax.plot(
        az_grid,
        alt_el_act,
        color=palette["success"],
        linestyle=":",
        linewidth=2.0,
        label=f"Elongasi sebenar ({elong_actual_deg:.2f}°)",
        zorder=2,
    )

    dx = 20 if right_side_free else -28
    dy = 4.2
    ax.annotate(
        f"Tinggi: {moon_alt_deg:.2f}°\nJarak Lengkung: {elong_actual_deg:.2f}°",
        xy=(moon_az_deg, moon_alt_deg),
        xytext=(moon_az_deg + dx, moon_alt_deg + dy),
        arrowprops=dict(arrowstyle="->", linewidth=1, color=palette["text_muted"]),
        fontsize=10,
        color=palette["text"],
        bbox=dict(
            boxstyle="round,pad=0.4,rounding_size=0.2",
            facecolor=palette["washed"],
            edgecolor=palette["border"],
        ),
        zorder=10,
    )

    ax.set_xlabel("Azimut (darjah)", color=palette["text"])
    ax.set_ylabel("Altitud (darjah)", color=palette["text"])
    ax.set_title(title, fontsize=14, fontweight="semibold", color=palette["text"], pad=22)
    if subtitle:
        ax.text(
            0.5,
            1.02,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=11,
            color=palette["text_muted"],
        )

    ax.set_ylim(y_min, y_max)
    if not wrap:
        ax.set_xlim(az_min, az_max)
    ax.tick_params(colors=palette["text_muted"])
    for spine in ax.spines.values():
        spine.set_color(palette["border"])
    ax.grid(True, linewidth=0.6, color=palette["border"], alpha=0.8)
    legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=True)
    legend.get_frame().set_edgecolor(palette["border"])
    legend.get_frame().set_facecolor(palette["white"])
    for text in legend.get_texts():
        text.set_color(palette["text"])

    fig.tight_layout()
    return fig
