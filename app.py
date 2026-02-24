from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from skyfield.api import load

from hilal.astro import evaluate_one_location, sample_moon_track
from hilal.constants import LOKASI_CERAPAN_MY
from hilal.plotting import plot_hilal_chart_pretty


@st.cache_resource
def load_ephemeris():
    ts = load.timescale()
    eph = load("de440.bsp")
    return ts, eph


def fig_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def render_single_location(ts, eph, d, tz_offset, alt_min, elong_min, show_plot, show_moonset):
    pilihan = st.selectbox("Lokasi Cerapan (Malaysia)", ["Custom (lat/lon manual)"] + list(LOKASI_CERAPAN_MY.keys()))
    if pilihan.startswith("Custom"):
        lat = st.number_input("Latitude", value=6.3500, format="%.6f")
        lon = st.number_input("Longitude", value=99.8000, format="%.6f")
        nama_lokasi = "Custom"
    else:
        lat, lon = LOKASI_CERAPAN_MY[pilihan]
        nama_lokasi = pilihan
        st.caption(f"Koordinat: {lat:.4f}, {lon:.4f}")

    res = evaluate_one_location(
        ts=ts,
        eph=eph,
        lat=lat,
        lon=lon,
        on_date=d,
        tz_offset=int(tz_offset),
        alt_min=float(alt_min),
        elong_min=float(elong_min),
        include_moonset=show_moonset,
    )
    if res is None:
        st.error("Tak jumpa waktu Maghrib (sunset) untuk tarikh/lokasi ini.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Maghrib (Sunset) - Local", res["sunset_local"].strftime("%Y-%m-%d %H:%M:%S"))
    c2.metric("Altitud Bulan @ Maghrib", f'{res["moon_alt_deg"]:.3f}°')
    c3.metric("Elongasi Sun-Moon", f'{res["elong_deg"]:.3f}°')
    c4.metric("Status Imkanur Rukyah", "LULUS" if res["passed"] else "TAK LULUS")

    if show_moonset and res["moonset_local"] is not None:
        st.caption(
            f"Moonset (local): {res['moonset_local'].strftime('%H:%M:%S')}  |  Lag time: {res['lag_minutes']:.1f} min"
        )

    details = pd.DataFrame(
        [
            {
                "Lokasi": nama_lokasi,
                "Latitude": lat,
                "Longitude": lon,
                "Tarikh": d.isoformat(),
                "Maghrib (local)": res["sunset_local"].strftime("%H:%M:%S"),
                "Moon Alt (°)": res["moon_alt_deg"],
                "Moon Az (°)": res["moon_az_deg"],
                "Sun Alt (°)": res["sun_alt_deg"],
                "Sun Az (°)": res["sun_az_deg"],
                "Elong (°)": res["elong_deg"],
                "Kriteria Alt >= (°)": alt_min,
                "Kriteria Elong >= (°)": elong_min,
                "Lulus": res["passed"],
                "Moonset (local)": res["moonset_local"].strftime("%H:%M:%S") if res["moonset_local"] else None,
                "Lag (min)": res["lag_minutes"],
            }
        ]
    )
    st.subheader("Butiran (1 lokasi)")
    st.dataframe(details, use_container_width=True)

    if show_plot:
        df_curve = sample_moon_track(ts, eph, lat, lon, res["t_sunset"], minutes_before=60, minutes_after=20, step_seconds=30)
        fig = plot_hilal_chart_pretty(
            df_curve=df_curve,
            sun_az_deg=res["sun_az_deg"],
            sun_alt_deg=res["sun_alt_deg"],
            moon_az_deg=res["moon_az_deg"],
            moon_alt_deg=res["moon_alt_deg"],
            alt_min_deg=float(alt_min),
            elong_min_deg=float(elong_min),
            elong_actual_deg=res["elong_deg"],
            title=f"Cerapan Hilal - {d.strftime('%d %B %Y')}",
            subtitle=f"Lokasi: {nama_lokasi}",
        )
        st.pyplot(fig)
        st.download_button(
            label="Download graf (PNG)",
            data=fig_to_png_bytes(fig),
            file_name=f"graf-hilal-{d.isoformat()}-{nama_lokasi[:40].replace(' ', '-')}.png",
            mime="image/png",
        )


def render_ranking(ts, eph, d, tz_offset, alt_min, elong_min, show_moonset):
    st.subheader("Semua lokasi (ranking) - Altitud & Elongasi @ Maghrib")
    rows = []
    for nama, (la, lo) in LOKASI_CERAPAN_MY.items():
        r = evaluate_one_location(
            ts=ts,
            eph=eph,
            lat=la,
            lon=lo,
            on_date=d,
            tz_offset=int(tz_offset),
            alt_min=float(alt_min),
            elong_min=float(elong_min),
            include_moonset=show_moonset,
        )
        if r is None:
            continue
        rows.append(
            {
                "Lokasi": nama,
                "Lat": la,
                "Lon": lo,
                "Maghrib": r["sunset_local"].strftime("%H:%M:%S"),
                "Alt (°)": r["moon_alt_deg"],
                "Elong (°)": r["elong_deg"],
                "Lulus": r["passed"],
                "Moonset": r["moonset_local"].strftime("%H:%M:%S") if (show_moonset and r["moonset_local"]) else None,
                "Lag (min)": r["lag_minutes"] if show_moonset else None,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        st.error("Tiada result (tak jumpa sunset). Check tarikh/UTC offset.")
        st.stop()

    df["LulusSort"] = df["Lulus"].astype(int)
    df = df.sort_values(by=["LulusSort", "Alt (°)", "Elong (°)"], ascending=[False, False, False]).drop(
        columns=["LulusSort"]
    )
    st.dataframe(df, use_container_width=True)
    st.metric("Bilangan lokasi LULUS", f"{int(df['Lulus'].sum())}/{len(df)}")


def main():
    st.set_page_config(page_title="Kiraan Hilal MABIMS (Malaysia)", layout="wide")
    st.title("Kiraan Hilal (Imkanur Rukyah MABIMS) - Altitud & Elongasi @ Maghrib")

    with st.sidebar:
        st.header("Input")
        mode = st.radio("Mode", ["Satu lokasi", "Semua lokasi (ranking)"], index=0)
        d = st.date_input("Tarikh Cerapan", value=date(2026, 3, 19))
        tz_offset = st.number_input("UTC Offset (Jam)", value=8, step=1)
        st.divider()
        st.subheader("Kriteria MABIMS")
        alt_min = st.number_input("Altitud Min (°)", value=3.0, step=0.1)
        elong_min = st.number_input("Elongasi Min (°)", value=6.4, step=0.1)
        st.divider()
        show_plot = st.checkbox("Plot graf Altitud vs Azimut (sekitar Maghrib)", value=True)
        show_moonset = st.checkbox("Kira Moonset & Lag Time (Moonset - Sunset)", value=True)

    ts, eph = load_ephemeris()
    if mode == "Satu lokasi":
        render_single_location(ts, eph, d, tz_offset, alt_min, elong_min, show_plot, show_moonset)
        st.info("Nota: Kriteria MABIMS: Alt >= 3° dan Elong >= 6.4°.")
        return

    render_ranking(ts, eph, d, tz_offset, alt_min, elong_min, show_moonset)
    st.info(
        "Tip: Bila banyak lokasi di barat (contoh Langkawi/Perak/Selangor) pun tak lulus, "
        "kebarangkalian nampak hilal dalam Malaysia biasanya rendah untuk tarikh itu."
    )


if __name__ == "__main__":
    main()
