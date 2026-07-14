import logging
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from skyfield.api import load

from hilal.astro import evaluate_one_location, sample_moon_track
from hilal.constants import LOKASI_CERAPAN_MY
from hilal.plotting import plot_hilal_chart_pretty
from hilal.ui import (
    inject_myds_styles,
    render_callout,
    render_footer,
    render_metrics,
    render_page_header,
    render_section_header,
    render_sidebar_header,
    render_status,
    render_table,
)


logger = logging.getLogger(__name__)


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


def render_single_location(
    ts,
    eph,
    d,
    tz_offset,
    alt_min,
    elong_min,
    show_plot,
    show_moonset,
    dark_mode,
):
    render_section_header(
        "Pilih lokasi cerapan",
        "Gunakan lokasi cerapan yang disenaraikan atau masukkan koordinat sendiri.",
        "Langkah 1",
    )
    pilihan = st.selectbox(
        "Lokasi cerapan di Malaysia",
        ["Koordinat sendiri"] + list(LOKASI_CERAPAN_MY.keys()),
        help="Senarai lokasi cerapan hilal di Malaysia.",
    )
    if pilihan == "Koordinat sendiri":
        lat_col, lon_col = st.columns(2)
        with lat_col:
            lat = st.number_input(
                "Latitud",
                min_value=-90.0,
                max_value=90.0,
                value=6.3500,
                format="%.6f",
                help="Nilai antara −90 hingga 90 darjah.",
            )
        with lon_col:
            lon = st.number_input(
                "Longitud",
                min_value=-180.0,
                max_value=180.0,
                value=99.8000,
                format="%.6f",
                help="Nilai antara −180 hingga 180 darjah.",
            )
        nama_lokasi = "Koordinat sendiri"
    else:
        lat, lon = LOKASI_CERAPAN_MY[pilihan]
        nama_lokasi = pilihan
        st.caption(f"Koordinat lokasi: {lat:.4f}° latitud, {lon:.4f}° longitud")

    with st.spinner("Mengira kedudukan matahari dan bulan…"):
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
        render_callout(
            "Pengiraan tidak dapat diselesaikan",
            "Waktu matahari terbenam tidak ditemui. Semak tarikh, koordinat dan zon waktu, kemudian cuba lagi.",
            "danger",
        )
        return

    render_section_header(
        "Ringkasan keputusan",
        f"Keputusan bagi {nama_lokasi} pada {d.strftime('%d/%m/%Y')}.",
        "Langkah 2",
    )
    render_metrics(
        [
            (
                "Matahari terbenam",
                res["sunset_local"].strftime("%H:%M:%S"),
                f"{d.strftime('%d/%m/%Y')} · UTC{int(tz_offset):+d}",
            ),
            ("Altitud bulan", f'{res["moon_alt_deg"]:.3f}°', f"Had minimum {alt_min:.1f}°"),
            (
                "Elongasi matahari–bulan",
                f'{res["elong_deg"]:.3f}°',
                f"Had minimum {elong_min:.1f}°",
            ),
        ]
    )
    render_status(res["passed"])

    if show_moonset and res["moonset_local"] is not None:
        st.caption(
            f"Bulan terbenam pada {res['moonset_local'].strftime('%H:%M:%S')} waktu tempatan "
            f"({res['lag_minutes']:.1f} minit selepas matahari terbenam)."
        )

    details = {
        "Lokasi": nama_lokasi,
        "Latitud": f"{lat:.4f}°",
        "Longitud": f"{lon:.4f}°",
        "Tarikh": d.strftime("%d/%m/%Y"),
        "Matahari terbenam": res["sunset_local"].strftime("%H:%M:%S"),
        "Altitud bulan": f'{res["moon_alt_deg"]:.3f}°',
        "Azimut bulan": f'{res["moon_az_deg"]:.3f}°',
        "Altitud matahari": f'{res["sun_alt_deg"]:.3f}°',
        "Azimut matahari": f'{res["sun_az_deg"]:.3f}°',
        "Elongasi": f'{res["elong_deg"]:.3f}°',
        "Keputusan": "Memenuhi" if res["passed"] else "Tidak memenuhi",
    }
    detail_columns = [
        ("Lokasi", "Lokasi"),
        ("Latitud", "Latitud"),
        ("Longitud", "Longitud"),
        ("Tarikh", "Tarikh"),
        ("Matahari terbenam", "Matahari terbenam"),
        ("Altitud bulan", "Altitud bulan"),
        ("Azimut bulan", "Azimut bulan"),
        ("Altitud matahari", "Altitud matahari"),
        ("Azimut matahari", "Azimut matahari"),
        ("Elongasi", "Elongasi"),
        ("Keputusan", "Keputusan"),
    ]
    numeric_columns = {
        "Latitud",
        "Longitud",
        "Matahari terbenam",
        "Altitud bulan",
        "Azimut bulan",
        "Altitud matahari",
        "Azimut matahari",
        "Elongasi",
    }
    if show_moonset:
        details["Bulan terbenam"] = (
            res["moonset_local"].strftime("%H:%M:%S") if res["moonset_local"] else "—"
        )
        details["Tempoh lengah"] = (
            f'{res["lag_minutes"]:.1f} minit' if res["lag_minutes"] is not None else "—"
        )
        detail_columns.extend(
            [("Bulan terbenam", "Bulan terbenam"), ("Tempoh lengah", "Tempoh lengah")]
        )
        numeric_columns.update({"Bulan terbenam", "Tempoh lengah"})

    render_section_header(
        "Butiran pengiraan",
        "Nilai astronomi yang digunakan untuk menilai kriteria kenampakan.",
        "Data",
    )
    render_table(
        [details],
        detail_columns,
        "Butiran pengiraan bagi satu lokasi",
        numeric_columns,
    )

    if show_plot:
        render_section_header(
            "Graf kedudukan hilal",
            "Perbandingan kedudukan bulan, matahari dan had kriteria pada waktu matahari terbenam.",
            "Visualisasi",
        )
        df_curve = sample_moon_track(
            ts,
            eph,
            lat,
            lon,
            res["t_sunset"],
            minutes_before=60,
            minutes_after=20,
            step_seconds=30,
        )
        fig = plot_hilal_chart_pretty(
            df_curve=df_curve,
            sun_az_deg=res["sun_az_deg"],
            sun_alt_deg=res["sun_alt_deg"],
            moon_az_deg=res["moon_az_deg"],
            moon_alt_deg=res["moon_alt_deg"],
            alt_min_deg=float(alt_min),
            elong_min_deg=float(elong_min),
            elong_actual_deg=res["elong_deg"],
            title=f"Cerapan hilal — {d.strftime('%d/%m/%Y')}",
            subtitle=f"Lokasi: {nama_lokasi}",
            dark_mode=dark_mode,
        )
        st.pyplot(fig, width="stretch")
        st.download_button(
            label="Muat turun graf (PNG)",
            data=fig_to_png_bytes(fig),
            file_name=f"graf-hilal-{d.isoformat()}-{nama_lokasi[:40].replace(' ', '-')}.png",
            mime="image/png",
            type="primary",
        )

    render_callout(
        "Kriteria yang digunakan",
        f"Altitud sekurang-kurangnya {alt_min:.1f}° dan elongasi sekurang-kurangnya {elong_min:.1f}°.",
    )


def render_ranking(ts, eph, d, tz_offset, alt_min, elong_min, show_moonset):
    render_section_header(
        "Perbandingan semua lokasi",
        "Lokasi disusun mengikut pematuhan kriteria, altitud bulan dan elongasi tertinggi.",
        "Analisis nasional",
    )
    rows = []
    with st.spinner("Mengira semua lokasi cerapan…"):
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
                    "Latitud": la,
                    "Longitud": lo,
                    "Matahari terbenam": r["sunset_local"].strftime("%H:%M:%S"),
                    "Altitud": r["moon_alt_deg"],
                    "Elongasi": r["elong_deg"],
                    "Keputusan": "Memenuhi" if r["passed"] else "Tidak memenuhi",
                    "Bulan terbenam": (
                        r["moonset_local"].strftime("%H:%M:%S")
                        if (show_moonset and r["moonset_local"])
                        else "—"
                    ),
                    "Tempoh lengah": r["lag_minutes"] if show_moonset else None,
                    "_lulus": r["passed"],
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        render_callout(
            "Tiada keputusan",
            "Semak tarikh dan zon waktu, kemudian cuba lagi.",
            "warning",
        )
        return

    df = df.sort_values(by=["_lulus", "Altitud", "Elongasi"], ascending=[False, False, False])
    passed_count = int(df["_lulus"].sum())
    best_altitude = float(df["Altitud"].max())
    render_metrics(
        [
            ("Memenuhi kriteria", f"{passed_count}/{len(df)}", "Daripada semua lokasi dinilai"),
            ("Lokasi dinilai", str(len(df)), d.strftime("Tarikh %d/%m/%Y")),
            ("Altitud tertinggi", f"{best_altitude:.3f}°", f"Had minimum {alt_min:.1f}°"),
        ]
    )

    formatted_rows = []
    for row in df.to_dict(orient="records"):
        formatted = {
            "Lokasi": row["Lokasi"],
            "Latitud": f'{row["Latitud"]:.4f}°',
            "Longitud": f'{row["Longitud"]:.4f}°',
            "Matahari terbenam": row["Matahari terbenam"],
            "Altitud": f'{row["Altitud"]:.3f}°',
            "Elongasi": f'{row["Elongasi"]:.3f}°',
            "Keputusan": row["Keputusan"],
        }
        if show_moonset:
            formatted["Bulan terbenam"] = row["Bulan terbenam"]
            formatted["Tempoh lengah"] = (
                f'{row["Tempoh lengah"]:.1f} minit' if pd.notna(row["Tempoh lengah"]) else "—"
            )
        formatted_rows.append(formatted)

    columns = [
        ("Lokasi", "Lokasi"),
        ("Latitud", "Latitud"),
        ("Longitud", "Longitud"),
        ("Matahari terbenam", "Matahari terbenam"),
        ("Altitud", "Altitud"),
        ("Elongasi", "Elongasi"),
        ("Keputusan", "Keputusan"),
    ]
    numeric_columns = {"Latitud", "Longitud", "Matahari terbenam", "Altitud", "Elongasi"}
    if show_moonset:
        columns.extend([("Bulan terbenam", "Bulan terbenam"), ("Tempoh lengah", "Tempoh lengah")])
        numeric_columns.update({"Bulan terbenam", "Tempoh lengah"})

    render_section_header(
        "Senarai kedudukan lokasi",
        "Jadual boleh ditatal secara mendatar pada skrin kecil.",
        "Kedudukan",
    )
    render_table(
        formatted_rows,
        columns,
        f"Kedudukan {len(formatted_rows)} lokasi cerapan pada {d.strftime('%d/%m/%Y')}",
        numeric_columns,
    )
    render_callout(
        "Cara membaca keputusan",
        "Jika lokasi di barat Semenanjung juga tidak memenuhi kriteria, kebarangkalian kenampakan hilal di Malaysia lazimnya lebih rendah.",
    )


def main():
    st.set_page_config(
        page_title="eHilal | Analisis kenampakan hilal",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    dark_mode = bool(st.session_state.dark_mode)
    inject_myds_styles(dark_mode)
    render_page_header()

    with st.sidebar:
        render_sidebar_header()
        st.subheader("Paparan")
        st.toggle(
            "Tema gelap",
            key="dark_mode",
            help="Tukar antara tema terang dan gelap. Pilihan kekal sepanjang sesi ini.",
        )
        st.divider()
        st.subheader("Tetapan analisis")
        st.caption("Tetapkan skop, tarikh dan kriteria sebelum meneliti keputusan.")
        mode = st.radio(
            "Skop analisis",
            ["Satu lokasi", "Semua lokasi"],
            index=0,
            help="Bandingkan satu lokasi atau semua lokasi cerapan yang disenaraikan.",
        )
        d = st.date_input(
            "Tarikh cerapan",
            value=date(2026, 3, 19),
            format="DD/MM/YYYY",
            help="Tarikh tempatan bagi cerapan hilal.",
        )
        tz_offset = st.number_input(
            "Zon waktu UTC (jam)",
            min_value=-12,
            max_value=14,
            value=8,
            step=1,
            help="Malaysia menggunakan UTC+8.",
        )
        st.divider()
        st.subheader("Kriteria MABIMS")
        st.caption("Nilai lalai: altitud 3.0° dan elongasi 6.4°.")
        alt_min = st.number_input(
            "Altitud minimum (°)",
            min_value=0.0,
            max_value=90.0,
            value=3.0,
            step=0.1,
        )
        elong_min = st.number_input(
            "Elongasi minimum (°)",
            min_value=0.0,
            max_value=180.0,
            value=6.4,
            step=0.1,
        )
        st.divider()
        st.subheader("Paparan tambahan")
        show_plot = st.checkbox("Papar graf altitud dan azimut", value=True)
        show_moonset = st.checkbox("Kira waktu bulan terbenam", value=True)

    try:
        with st.spinner("Memuatkan data ephemeris…"):
            ts, eph = load_ephemeris()
    except Exception:
        logger.exception("Data ephemeris tidak dapat dimuatkan")
        render_callout(
            "Data ephemeris tidak dapat dimuatkan",
            "Pastikan fail de440.bsp tersedia atau sambungan internet dibenarkan untuk muat turun kali pertama.",
            "danger",
        )
        render_footer()
        return

    if mode == "Satu lokasi":
        render_single_location(
            ts,
            eph,
            d,
            tz_offset,
            alt_min,
            elong_min,
            show_plot,
            show_moonset,
            dark_mode,
        )
    else:
        render_ranking(ts, eph, d, tz_offset, alt_min, elong_min, show_moonset)

    render_footer()


if __name__ == "__main__":
    main()
