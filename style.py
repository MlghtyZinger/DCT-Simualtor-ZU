"""Shared look for every page: colours, type, chart template and small HTML helpers.
Design pass with unslop by Damir Sokolovsky (@heydamir), CC BY 4.0.
"""
import html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# neutral ramp (light, a touch of sand) + one sea-teal accent
INK, INK_2, INK_3 = "#1F1B16", "#5E554A", "#7B7266"
LINE = "#E4DFD6"
SURFACE, RAISED, CARD = "#FAF9F6", "#F2F0EB", "#FFFFFF"
ACCENT = "#0E6E6B"
NEUTRAL_SERIES = "#B9B1A4"

# Go / Okay / Skip: dot colour, soft tint, ink for text on the tint
STATUS = {
    "Go":   {"dot": "#2E8B6F", "tint": "#E3F0E9", "ink": "#1E6A53"},
    "Okay": {"dot": "#D3A23A", "tint": "#F6ECD2", "ink": "#7A5810"},
    "Skip": {"dot": "#C8583F", "tint": "#F5DED7", "ink": "#963826"},
}
EASE = "cubic-bezier(0.22, 1, 0.36, 1)"

_CSS = f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap");
/* headings: lighter, size carries hierarchy */
h1 {{ font-weight: 500 !important; font-size: 2rem !important; letter-spacing: -0.01em; }}
h2 {{ font-weight: 500 !important; font-size: 1.5rem !important; }}
h3 {{ font-weight: 500 !important; font-size: 1.125rem !important; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}           /* no anchor-link icons */
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; font-weight: 500; }}
[data-testid="stCaptionContainer"] {{ color: {INK_3}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
button, [data-baseweb="tab"] {{ transition: background-color 150ms {EASE}, color 150ms {EASE}, border-color 150ms {EASE}; }}

/* verdict */
.adh-verdict {{ display: flex; align-items: baseline; gap: 12px; margin: 8px 0 4px; }}
.adh-verdict .word {{ font-size: 1.75rem; font-weight: 500; line-height: 1.1; }}
.adh-verdict .msg {{ color: {INK_2}; font-size: 1rem; }}
.adh-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }}
.adh-legend {{ display: flex; gap: 20px; flex-wrap: wrap; color: {INK_2}; font-size: 0.875rem; margin: 0 0 8px; }}

/* day tiles (Check my dates) */
.adh-tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: 8px; margin: 12px 0 4px; }}
.adh-tile {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; padding: 12px; display: flex;
             flex-direction: column; gap: 4px; min-height: 120px; }}
.adh-tile .dow {{ color: {INK_3}; font-size: 0.75rem; }}
.adh-tile .day {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 1.25rem; font-weight: 500; font-variant-numeric: tabular-nums; }}
.adh-tile .st {{ font-size: 0.8125rem; font-weight: 500; }}
.adh-tile .tmp {{ color: {INK_2}; font-size: 0.8125rem; font-variant-numeric: tabular-nums; }}

/* signature: event marker = short accent rule + short name */
.adh-ev {{ display: block; font-size: 0.75rem; color: {INK}; line-height: 1.3; padding-top: 4px; margin-top: auto;
           border-top: 2px solid {ACCENT}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.adh-ev-inline {{ display: inline-block; border-top: 2px solid {ACCENT}; padding-top: 2px; font-size: 0.75rem; }}

/* month calendar */
.adh-months {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px 32px; margin: 8px 0 16px; }}
.adh-month {{ min-width: 0; }}
.adh-month h4 {{ font-size: 1rem; font-weight: 500; margin: 0 0 8px; padding: 0; }}
.adh-grid {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }}
.adh-grid .hd {{ color: {INK_3}; font-size: 0.75rem; text-align: center; padding-bottom: 4px; }}
.adh-cell {{ border-radius: 6px; min-height: 52px; min-width: 0; padding: 4px 6px; display: flex; flex-direction: column;
             font-variant-numeric: tabular-nums; }}
.adh-cell .n {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 0.8125rem; }}
.adh-cell .e {{ font-size: 0.6875rem; line-height: 1.2; margin-top: auto; border-top: 2px solid {ACCENT};
                padding-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: {INK}; }}
.adh-cell.past {{ color: {INK_3}; background: transparent; }}
.adh-cell.today {{ outline: 1.5px solid {INK}; outline-offset: -1.5px; }}
.adh-card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; padding: 20px; }}
</style>
"""


def apply():
    st.markdown(_CSS, unsafe_allow_html=True)


def dot(verdict: str) -> str:
    return f'<span class="adh-dot" style="background:{STATUS[verdict]["dot"]}"></span>'


def esc(s) -> str:
    return html.escape(str(s))


# ---- plotly: quiet grid, muted mono labels, accent first ---------------------------------
pio.templates["adh"] = go.layout.Template(layout=go.Layout(
    font=dict(family="IBM Plex Sans, sans-serif", size=13, color=INK_2),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[ACCENT, NEUTRAL_SERIES, "#D3A23A", "#7B7266"],
    xaxis=dict(gridcolor="rgba(31,27,22,0.06)", linecolor=LINE, zeroline=False,
               tickfont=dict(family="IBM Plex Mono, monospace", size=11, color=INK_3)),
    yaxis=dict(gridcolor="rgba(31,27,22,0.06)", linecolor=LINE, zeroline=False,
               tickfont=dict(family="IBM Plex Mono, monospace", size=11, color=INK_3)),
    hoverlabel=dict(bgcolor=CARD, bordercolor=LINE, font=dict(color=INK, family="IBM Plex Sans, sans-serif")),
    legend=dict(font=dict(color=INK_2)),
))
pio.templates.default = "plotly+adh"
