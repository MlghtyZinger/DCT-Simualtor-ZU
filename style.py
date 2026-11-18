"""Shared look for every page: colours (light + dark), type, charts, tables and HTML helpers.
Design pass with unslop by Damir Sokolovsky (@heydamir), CC BY 4.0.
"""
import html

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---- palettes: one neutral ramp with a touch of sand, one sea-teal accent -------------------
LIGHT = dict(bg="#FAF9F6", surface="#F2F0EB", card="#FFFFFF", raised="#F2F0EB", line="#E4DFD6",
             ink="#1F1B16", ink2="#5E554A", ink3="#7B7266", accent="#0E6E6B", accent_soft="#DCEDEC",
             go_dot="#2E8B6F", go_tint="#E3F0E9", go_ink="#1E6A53",
             ok_dot="#D3A23A", ok_tint="#F6ECD2", ok_ink="#7A5810",
             sk_dot="#C8583F", sk_tint="#F5DED7", sk_ink="#963826",
             dim="#F2F0EB", series="#B9B1A4", grid="rgba(31,27,22,0.06)")
DARK = dict(bg="#161513", surface="#12110F", card="#1C1A18", raised="#262421", line="#2F2C28",
            ink="#EFE9DE", ink2="#AAA398", ink3="#8A847A", accent="#3FB8B1", accent_soft="#173634",
            go_dot="#4CB892", go_tint="#1C3229", go_ink="#9AD9BE",
            ok_dot="#E0B04E", ok_tint="#352C1A", ok_ink="#EAC97A",
            sk_dot="#E07A62", sk_tint="#3A231E", sk_ink="#F0A893",
            dim="#1C1A18", series="#6F685E", grid="rgba(239,233,222,0.07)")

# kept for older imports (light values)
INK, INK_2, INK_3, LINE = LIGHT["ink"], LIGHT["ink2"], LIGHT["ink3"], LIGHT["line"]
ACCENT, NEUTRAL_SERIES = LIGHT["accent"], LIGHT["series"]
STATUS = {"Go": {"dot": LIGHT["go_dot"], "tint": LIGHT["go_tint"], "ink": LIGHT["go_ink"]},
          "Okay": {"dot": LIGHT["ok_dot"], "tint": LIGHT["ok_tint"], "ink": LIGHT["ok_ink"]},
          "Skip": {"dot": LIGHT["sk_dot"], "tint": LIGHT["sk_tint"], "ink": LIGHT["sk_ink"]}}
EASE = "cubic-bezier(0.22, 1, 0.36, 1)"


def is_dark() -> bool:
    return st.session_state.get("theme_mode", "light") == "dark"


def pal() -> dict:
    return DARK if is_dark() else LIGHT


def _vars(p: dict) -> str:
    return ":root{" + "".join(f"--{k.replace('_', '-')}:{v};" for k, v in p.items()) + "}"


_BASE = f"""
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap");
h1 {{ font-weight: 500 !important; font-size: 2rem !important; letter-spacing: -0.01em; }}
h2 {{ font-weight: 500 !important; font-size: 1.5rem !important; }}
h3 {{ font-weight: 500 !important; font-size: 1.125rem !important; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; font-weight: 500; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
button, [data-baseweb="tab"] {{ transition: background-color 150ms {EASE}, color 150ms {EASE}, border-color 150ms {EASE}; }}
.mono {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-variant-numeric: tabular-nums; }}

/* status */
.adh-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:1px; }}
.dot-Go {{ background: var(--go-dot); }} .dot-Okay {{ background: var(--ok-dot); }} .dot-Skip {{ background: var(--sk-dot); }}
.st-Go {{ background: var(--go-tint); color: var(--go-ink); }}
.st-Okay {{ background: var(--ok-tint); color: var(--ok-ink); }}
.st-Skip {{ background: var(--sk-tint); color: var(--sk-ink); }}
.ink-Go {{ color: var(--go-ink); }} .ink-Okay {{ color: var(--ok-ink); }} .ink-Skip {{ color: var(--sk-ink); }}
.adh-legend {{ display:flex; gap:20px; flex-wrap:wrap; color:var(--ink2); font-size:0.875rem; margin:0 0 8px; }}
.adh-muted {{ color: var(--ink2); }}

/* summary card (Check my dates) */
.adh-summary {{ display:grid; grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(120px, 1fr)); gap: 24px;
               background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px 24px; margin: 8px 0 16px; }}
.adh-summary .word {{ font-size: 1.75rem; font-weight: 500; line-height: 1.1; }}
.adh-summary .msg {{ color: var(--ink2); font-size: 0.9375rem; margin-top: 4px; }}
.adh-summary .lab {{ color: var(--ink3); font-size: 0.8125rem; }}
.adh-summary .val {{ font-size: 1.25rem; font-weight: 500; margin-top: 4px; font-variant-numeric: tabular-nums; }}
.adh-summary .sub {{ color: var(--ink2); font-size: 0.8125rem; margin-top: 2px; }}
@media (max-width: 760px) {{ .adh-summary {{ grid-template-columns: 1fr 1fr; }} }}

/* month calendar */
.adh-months {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 32px 40px; margin: 8px 0 16px; }}
.adh-month {{ min-width: 0; }}
.adh-month h4 {{ font-size: 1rem; font-weight: 500; margin: 0 0 8px; padding: 0; color: var(--ink); }}
.adh-grid {{ display:grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }}
.adh-grid .hd {{ color: var(--ink3); font-size: 0.75rem; text-align: center; padding-bottom: 4px; }}
.adh-cell {{ position: relative; border-radius: 6px; min-height: 64px; min-width: 0; padding: 4px 6px;
             display:flex; flex-direction: column; gap: 2px; }}
.adh-cell .n {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 0.8125rem; }}
.adh-cell .e {{ font-size: 0.6875rem; line-height: 1.25; color: var(--ink); border-left: 2px solid var(--accent);
                padding-left: 4px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
                overflow-wrap: normal; word-break: normal; }}
.adh-cell.off {{ color: var(--ink3); background: transparent; }}
.adh-cell.dim {{ background: var(--dim); color: var(--ink3); }}
.adh-cell.today {{ outline: 1.5px solid var(--ink); outline-offset: -1.5px; }}
.adh-cell.pick {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
.adh-cell .badge {{ position:absolute; top:4px; right:4px; background: var(--accent); color: var(--card); border-radius: 4px;
                    font-size: 0.6875rem; font-weight: 600; padding: 0 5px; line-height: 16px; }}
.adh-mev {{ list-style: none; margin: 8px 0 0; padding: 0; font-size: 0.8125rem; color: var(--ink2); }}
.adh-mev li {{ padding: 2px 0 2px 8px; border-left: 2px solid var(--accent); margin: 4px 0; }}
.adh-mev b {{ color: var(--ink); font-weight: 500; font-variant-numeric: tabular-nums; }}

/* suggester list */
.adh-picks {{ list-style: none; margin: 4px 0 12px; padding: 0; }}
.adh-picks li {{ padding: 6px 0; color: var(--ink2); font-size: 0.9375rem; }}
.adh-picks b {{ color: var(--ink); font-weight: 500; }}
.adh-picks .badge-n {{ display:inline-block; min-width: 18px; text-align:center; background: var(--accent); color: var(--card);
                      border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 8px; line-height: 18px; }}

/* tables */
.adh-table {{ max-height: 440px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; margin-bottom: 16px; }}
.adh-table table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; font-variant-numeric: tabular-nums; }}
.adh-table th {{ position: sticky; top: 0; background: var(--raised); color: var(--ink2); font-weight: 500; text-align: left;
                 padding: 8px 12px; border-bottom: 1px solid var(--line); }}
.adh-table td {{ padding: 8px 12px; border-bottom: 1px solid var(--line); color: var(--ink); }}
.adh-table tr:last-child td {{ border-bottom: none; }}
"""

# Streamlit widgets in dark mode (the theme file is light; these rules flip it per visitor)
_DARK_WIDGETS = """
.stApp, [data-testid="stHeader"], [data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div { background-color: var(--bg) !important; }
[data-testid="stSidebar"], [data-testid="stSidebarContent"] { background-color: var(--surface) !important; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp span,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] p, [data-testid="stSidebarNav"] span { color: var(--ink); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--ink3) !important; }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"],
[data-testid="stChatInput"] > div, [data-testid="stNumberInputContainer"] { background-color: var(--raised) !important; border-color: var(--line) !important; }
[data-testid="stDateInputField"], [data-testid="stDateInput"] [role="group"], [data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"], .react-aria-ComboBox [role="group"] { background-color: var(--raised) !important; border-color: var(--line) !important; }
.react-aria-Popover, [data-testid="stSelectboxVirtualDropdown"], [role="listbox"] { background-color: var(--card) !important; color: var(--ink) !important; }
[data-testid="stSelectbox"] svg, [data-testid="stNumberInput"] svg { color: var(--ink2) !important; }
[data-testid="stDateInput"] [role="spinbutton"], [data-testid="stDateInput"] span { color: var(--ink) !important; }
[data-testid="stDateInput"] input { background-color: transparent !important; }
input::placeholder { color: var(--ink3) !important; -webkit-text-fill-color: var(--ink3) !important; }
input, textarea { color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; background: transparent !important; }
[data-baseweb="select"] div, [data-baseweb="select"] svg { color: var(--ink) !important; fill: var(--ink2); }
button[kind="secondary"], button[kind="secondaryFormSubmit"], [data-testid="stNumberInput"] button,
[data-testid="stButtonGroup"] button { background-color: var(--card) !important; color: var(--ink) !important; border-color: var(--line) !important; }
[data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[kind*="Active"] { background-color: var(--accent-soft) !important; color: var(--accent) !important; border-color: var(--accent) !important; }
button[kind="tertiary"], button[kind="tertiary"] p { color: var(--ink) !important; }
button[kind="primary"], button[kind="primaryFormSubmit"] { background-color: var(--accent) !important; border-color: var(--accent) !important; color: #0B1F1E !important; }
button[kind="primary"] p, button[kind="primaryFormSubmit"] p { color: #0B1F1E !important; }
.stTabs [data-baseweb="tab-list"] { border-bottom-color: var(--line) !important; }
.stTabs [data-baseweb="tab"] p { color: var(--ink2); } .stTabs [aria-selected="true"] p { color: var(--accent) !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent) !important; }
.stTabs [data-baseweb="tab-border"] { background-color: var(--line) !important; }
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"] { border-color: var(--line) !important; }
[data-testid="stAlertContainer"] { background-color: var(--raised) !important; color: var(--ink) !important; }
[data-testid="stChatMessage"] { background-color: var(--card) !important; }
[data-baseweb="popover"] > div, [data-baseweb="calendar"], [data-baseweb="menu"], [role="listbox"] { background-color: var(--card) !important; color: var(--ink) !important; }
[data-baseweb="calendar"] div, [role="option"] { color: var(--ink); background-color: transparent; }
[data-testid="stSlider"] [data-testid="stSliderThumbValue"], [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: var(--accent) !important; }
[data-testid="stExpander"] details { border-color: var(--line) !important; background: var(--card); }
hr { border-color: var(--line) !important; }
[data-testid="stTextInputRootElement"], [data-testid="stTextInput"] [data-baseweb="input"] { background-color: var(--raised) !important; border-color: var(--line) !important; }
[data-testid="stMetricDelta"] { background-color: var(--raised) !important; color: var(--ink2) !important; }
[data-testid="stMetricDelta"] svg { color: var(--ink2) !important; }
pre, code, [data-testid="stCode"] { background-color: var(--raised) !important; color: var(--ink) !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:focus-visible { background-color: var(--card) !important; color: var(--ink) !important; }
[data-testid="stExpander"] summary *, [data-testid="stExpander"] summary svg { color: var(--ink) !important; }
[data-testid="stDateInputCalendar"] { background-color: var(--card) !important; color: var(--ink) !important; border-color: var(--line) !important; }
[data-testid="stDateInputCalendar"] select { background-color: var(--raised) !important; color: var(--ink) !important; border-color: var(--line) !important; }
[data-testid="stDateInputCalendar"] [role="gridcell"], [data-testid="stDateInputCalendar"] th,
[data-testid="stDateInputCalendar"] button, [data-testid="stDateInputCalendar"] svg { color: var(--ink); }
[data-testid="stDateInputCalendar"] [data-disabled="true"], [data-testid="stDateInputCalendar"] [data-outside-month="true"] { color: var(--ink3) !important; opacity: 0.6; }
[data-testid="stDateInputCalendar"] [role="gridcell"] [role="button"]:not([data-disabled="true"]):not([data-selected="true"]) { color: var(--ink); }
/* top-right toolbar (Share, star, edit, GitHub, menu) */
[data-testid="stToolbar"], [data-testid="stToolbar"] *, [data-testid="stToolbarActions"] *, [data-testid="stMainMenu"] *,
[data-testid="stAppDeployButton"] *, [data-testid="stHeader"] button, [data-testid="stHeader"] a { color: var(--ink) !important; }
[data-testid="stToolbar"] svg, [data-testid="stHeader"] svg { color: var(--ink) !important; }
[data-testid="stToolbarActionButtonIcon"], [data-testid="stToolbarActionButton"] img,
[data-testid="stToolbarActionButton"] svg { filter: invert(1) brightness(1.15) !important; opacity: 1 !important; }
[data-testid="stToolbarActionButton"] button, [data-testid="stToolbar"] button[kind="headerButton"],
[data-testid="stToolbar"] button[kind="header"] { background-color: transparent !important; opacity: 1 !important; }
[data-testid="stToolbarActionButton"] button:hover { background-color: var(--raised) !important; }
[data-testid="stToolbar"] button:hover, [data-testid="stHeader"] button:hover { background-color: var(--raised) !important; }
[data-testid="stMainMenuPopover"], [data-testid="stMainMenuList"] { background-color: var(--card) !important; color: var(--ink) !important; }
[role="radiogroup"] label > div:first-child:not([class*="checked"]) { border-color: var(--ink3); }
"""


def apply():
    p = pal()
    css = _vars(p) + _BASE + (_DARK_WIDGETS if is_dark() else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def theme_switch():
    """Sun / moon control in the sidebar; remembered for this visitor's session."""
    with st.sidebar:
        st.segmented_control("Theme", [":material/light_mode:", ":material/dark_mode:"],
                             default=":material/dark_mode:" if is_dark() else ":material/light_mode:",
                             key="_theme_pick", label_visibility="collapsed", on_change=_flip)


def _flip():
    v = st.session_state.get("_theme_pick")
    if v:
        st.session_state.theme_mode = "dark" if "dark" in v else "light"


def dot(verdict: str) -> str:
    return f'<span class="adh-dot dot-{verdict}"></span>'


def esc(s) -> str:
    return html.escape(str(s))


# ---- tables as HTML so they follow light / dark ------------------------------------------------
def table(container, obj=None, **_):
    """table(st, df_or_styler) or table(column, df_or_styler); hides the index."""
    if obj is None:
        container, obj = st, container
    sty = obj if hasattr(obj, "to_html") and not isinstance(obj, pd.DataFrame) else obj.style
    container.markdown(f'<div class="adh-table">{sty.hide(axis="index").to_html()}</div>', unsafe_allow_html=True)


# ---- charts: quiet grid, muted mono labels, accent first; follows light / dark ---------------
def _template(p):
    ax = dict(gridcolor=p["grid"], linecolor=p["line"], zeroline=False,
              tickfont=dict(family="IBM Plex Mono, monospace", size=11, color=p["ink3"]),
              title=dict(font=dict(color=p["ink2"])))
    return go.layout.Template(layout=go.Layout(
        font=dict(family="IBM Plex Sans, sans-serif", size=13, color=p["ink2"]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[p["accent"], p["series"], p["ok_dot"], p["ink3"]], xaxis=ax, yaxis=ax,
        hoverlabel=dict(bgcolor=p["card"], bordercolor=p["line"], font=dict(color=p["ink"], family="IBM Plex Sans, sans-serif")),
        legend=dict(font=dict(color=p["ink2"]))))


pio.templates["adh_light"], pio.templates["adh_dark"] = _template(LIGHT), _template(DARK)


def chart(fig, **kw):
    p = pal()
    fig.update_layout(template="plotly+adh_dark" if is_dark() else "plotly+adh_light")
    # swap fixed light colours for their dark versions
    swap = {LIGHT[k]: p[k] for k in ("accent", "series", "ink", "ink2", "ink3")} if is_dark() else {}
    if swap:
        for tr in fig.data:
            m = getattr(tr, "marker", None)
            if m is not None and m.color is not None:
                c = m.color
                m.color = [swap.get(x, x) for x in c] if isinstance(c, (list, tuple)) else swap.get(c, c)
            ln = getattr(tr, "line", None)
            if ln is not None and ln.color is not None:
                ln.color = swap.get(ln.color, ln.color)
    st.plotly_chart(fig, width="stretch", theme=None, **kw)
