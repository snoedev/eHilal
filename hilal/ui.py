"""MYDS-equivalent presentation helpers for the Streamlit interface."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import streamlit as st


_STYLESHEET = Path(__file__).resolve().parent.parent / "assets" / "myds.css"


def inject_myds_styles(dark_mode: bool) -> None:
    """Load the local token-backed stylesheet and expose the selected theme."""
    css = _STYLESHEET.read_text(encoding="utf-8")
    theme = "dark" if dark_mode else "light"
    st.markdown(
        f"<style>\n{css}\n</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="myds-theme-marker myds-theme-marker--{theme}" '
        f'data-theme="{theme}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def render_sidebar_header() -> None:
    """Render compact product identity inside the settings sidebar."""
    st.markdown(
        """
        <div class="myds-sidebar-brand">
          <span class="myds-sidebar-brand__name">eHilal</span>
          <span class="myds-sidebar-brand__description">Analisis kenampakan hilal Malaysia</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header() -> None:
    """Render the page identity without a government masthead."""
    st.markdown(
        """
        <header class="myds-page-header">
          <span class="myds-tag myds-tag--primary">Alat pengiraan falak</span>
          <h1 class="myds-page-header__title">Analisis kenampakan hilal</h1>
          <p class="myds-page-header__description">
            Nilai altitud bulan dan elongasi ketika matahari terbenam berdasarkan
            kriteria Imkanur Rukyah MABIMS.
          </p>
          <dl class="myds-page-header__meta" aria-label="Maklumat analisis">
            <div><dt>Kaedah</dt><dd>Imkanur Rukyah</dd></div>
            <div><dt>Wilayah</dt><dd>Malaysia</dd></div>
            <div><dt>Zon waktu lalai</dt><dd>UTC+8</dd></div>
          </dl>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, description: str | None = None, eyebrow: str | None = None) -> None:
    """Render a consistent H2 section heading and supporting copy."""
    eyebrow_html = f'<span class="myds-section-header__eyebrow">{escape(eyebrow)}</span>' if eyebrow else ""
    description_html = (
        f'<p class="myds-section-header__description">{escape(description)}</p>' if description else ""
    )
    st.markdown(
        f"""
        <div class="myds-section-header">
          {eyebrow_html}
          <h2>{escape(title)}</h2>
          {description_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(items: Sequence[tuple[str, str, str | None]]) -> None:
    """Render responsive summary cards with clear label-value hierarchy."""
    cards = []
    for label, value, helper in items:
        helper_html = f'<span class="myds-metric__helper">{escape(helper)}</span>' if helper else ""
        cards.append(
            '<div class="myds-metric">'
            f'<dt>{escape(label)}</dt>'
            f'<dd>{escape(value)}</dd>'
            f'{helper_html}'
            '</div>'
        )
    st.html(f'<dl class="myds-metric-grid">{"".join(cards)}</dl>')


def render_status(passed: bool) -> None:
    """Render a non-colour-only outcome message."""
    if passed:
        modifier = "success"
        mark = "✓"
        title = "Memenuhi kriteria MABIMS"
        description = "Altitud bulan dan elongasi mencapai kedua-dua nilai minimum yang ditetapkan."
    else:
        modifier = "danger"
        mark = "!"
        title = "Tidak memenuhi kriteria MABIMS"
        description = "Sekurang-kurangnya satu nilai berada di bawah had minimum yang ditetapkan."

    st.markdown(
        f"""
        <div class="myds-status myds-status--{modifier}" role="status">
          <span class="myds-status__mark" aria-hidden="true">{mark}</span>
          <div>
            <span class="myds-status__title">{escape(title)}</span>
            <span class="myds-status__description">{escape(description)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_callout(title: str, description: str, variant: str = "info") -> None:
    """Render an accessible token-backed callout."""
    role = "alert" if variant == "danger" else "note"
    st.markdown(
        f"""
        <aside class="myds-callout myds-callout--{escape(variant)}" role="{role}">
          <strong>{escape(title)}</strong>
          <span>{escape(description)}</span>
        </aside>
        """,
        unsafe_allow_html=True,
    )


def render_table(
    rows: Iterable[Mapping[str, object]],
    columns: Sequence[tuple[str, str]],
    caption: str,
    numeric_columns: set[str] | None = None,
) -> None:
    """Render a semantic, horizontally scrollable MYDS-equivalent table."""
    numeric_columns = numeric_columns or set()
    rows = list(rows)
    headers = "".join(
        f'<th scope="col" class="{"myds-table__numeric" if key in numeric_columns else ""}">'
        f"{escape(label)}</th>"
        for key, label in columns
    )

    body_rows = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "—")
            display = "—" if value is None or value == "" else str(value)
            classes = ["myds-table__numeric"] if key in numeric_columns else []
            if key == "Keputusan":
                passed = display == "Memenuhi"
                modifier = "success" if passed else "danger"
                display_html = (
                    f'<span class="myds-tag myds-tag--{modifier}">'
                    f'<span class="myds-tag__dot" aria-hidden="true"></span>{escape(display)}</span>'
                )
            else:
                display_html = escape(display)
            cells.append(f'<td class="{" ".join(classes)}">{display_html}</td>')
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    if body_rows:
        body = "".join(body_rows)
    else:
        body = f'<tr><td class="myds-table__empty" colspan="{len(columns)}">Tiada data untuk dipaparkan.</td></tr>'

    st.markdown(
        f"""
        <div class="myds-table-region" role="region" aria-label="{escape(caption)}" tabindex="0">
          <table class="myds-table">
            <caption>{escape(caption)}</caption>
            <thead><tr>{headers}</tr></thead>
            <tbody>{body}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Render a compact product note without inventing agency identity."""
    st.markdown(
        """
        <footer class="myds-footer">
          <strong>Nota penggunaan</strong>
          <span>
            eHilal ialah alat sokongan pengiraan. Keputusan rasmi cerapan dan pengisytiharan
            tarikh hendaklah dirujuk kepada pihak berkuasa berkaitan.
          </span>
        </footer>
        """,
        unsafe_allow_html=True,
    )
