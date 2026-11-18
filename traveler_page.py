"""Traveler page – open to guests. Simple answers only: no guest numbers, no DCT data.
Busy/quiet = LightGBM forecast (data/traveler_forecast.csv, made by train_traveler_model.py).
Weather   = Open-Meteo (free, no key): live forecast for ~16 days, typical weather after that.
"""
from datetime import date, timedelta
from pathlib import Path
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

import style
from style import STATUS, dot, esc

from calendar_ad import NOTES, LAST_DAY, MAJOR, SHORT, LONG, events_on

DATA = Path(__file__).parent / "data"
LAT, LON = 24.45, 54.38  # Abu Dhabi
TODAY = date.today()
END = LAST_DAY.date()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
COLOR = {"Go": "#2f9e44", "Okay": "#f2c12e", "Skip": "#e03131"}
ICON = {k: dot(k) for k in ("Go", "Okay", "Skip")}   # small coloured dot (HTML)
# fallback typical highs/lows (°C) if the weather service can't be reached
TYPICAL = {1: (24, 14), 2: (26, 15), 3: (29, 18), 4: (34, 22), 5: (39, 26), 6: (41, 29),
           7: (42, 31), 8: (42, 31), 9: (40, 28), 10: (36, 24), 11: (31, 19), 12: (26, 16)}


# ------------------------------------------------------------------------- data
@st.cache_data
def load_forecast():
    f = pd.read_csv(DATA / "traveler_forecast.csv", parse_dates=["Date"]).fillna("")
    return f.set_index("Date")


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def live_weather():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=10, params={
            "latitude": LAT, "longitude": LON, "timezone": "Asia/Dubai", "forecast_days": 16,
            "daily": "temperature_2m_max,temperature_2m_min"})
        j = r.json()["daily"]
        return pd.DataFrame({"High": j["temperature_2m_max"], "Low": j["temperature_2m_min"]},
                            index=pd.to_datetime(j["time"]))
    except Exception:
        return None


@st.cache_data(ttl=30 * 24 * 3600, show_spinner=False)
def typical_weather():
    """Average of the last 10 years for each day of the year (smoothed)."""
    try:
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=20, params={
            "latitude": LAT, "longitude": LON, "timezone": "Asia/Dubai",
            "start_date": "2016-01-01", "end_date": "2025-12-31",
            "daily": "temperature_2m_max,temperature_2m_min"})
        j = r.json()["daily"]
        w = pd.DataFrame({"High": j["temperature_2m_max"], "Low": j["temperature_2m_min"]},
                         index=pd.to_datetime(j["time"]))
        w = w.groupby(w.index.dayofyear).mean()
        w = pd.concat([w.tail(15), w, w.head(15)]).rolling(31, center=True).mean().iloc[15:-15]
        return w.round(0)
    except Exception:
        return None


def build_days(start, end) -> pd.DataFrame:
    f = load_forecast().loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    live, typ = live_weather(), typical_weather()
    hi, lo, src = [], [], []
    for d in f.index:
        if live is not None and d in live.index:
            hi.append(live.High[d]); lo.append(live.Low[d]); src.append("forecast")
        elif typ is not None:
            doy = min(d.dayofyear, 365)
            hi.append(typ.High[doy]); lo.append(typ.Low[doy]); src.append("typical")
        else:
            hi.append(TYPICAL[d.month][0]); lo.append(TYPICAL[d.month][1]); src.append("typical")
    f["High"], f["Low"], f["WeatherSource"] = [round(x) for x in hi], [round(x) for x in lo], src
    f["Events"] = [events_on(d) for d in f.index]                       # all holidays + events that day
    f["Event"] = f.Events.map(", ".join)
    f["Major"] = f.Events.map(lambda ev: any(e in MAJOR for e in ev))
    f.loc[f.Major, "Busy"] = "Busy"                                     # big events fill hotels
    f["Label"] = f.Events.map(lambda ev: " + ".join(dict.fromkeys(SHORT.get(e, e) for e in ev if e not in LONG)))
    busy_pts = f.Busy.map({"Quiet": 0, "Average": 1, "Busy": 2})
    heat_pts = pd.cut(f.High, [-99, 32, 36, 40, 99], labels=[0, 1, 2, 4]).astype(int)
    score = busy_pts + heat_pts
    f["Verdict"] = pd.cut(score, [-1, 1, 3, 99], labels=["Go", "Okay", "Skip"]).astype(str)
    f["Weather"] = pd.cut(f.High, [-99, 32, 36, 40, 99],
                          labels=["Pleasant", "Warm", "Hot", "Very hot"]).astype(str)
    f["Reason"] = [_reason(r) for r in f.itertuples()]
    return f


def _reason(r):
    busy = {"Quiet": "Quiet", "Average": "Normal crowds", "Busy": "Busy"}[r.Busy]
    parts = [busy, f"{r.Weather.lower()} ({r.High}°C)"]
    if r.Event:
        parts.append(r.Event)
    if r.School:
        parts.append(r.School + " (approx.)")
    return " · ".join(parts)


def event_names(days: pd.DataFrame) -> list:
    """Every holiday/event in these days, in order of first appearance."""
    return list(dict.fromkeys(e for ev in days.Events for e in ev))


def spans(days: pd.DataFrame, name: str) -> str:
    """'01 Dec – 03 Dec, 09 Dec – 17 Dec' for the days an event is on."""
    on = [d for d, e in days.Events.items() if name in e]
    out, start, prev = [], on[0], on[0]
    for d in on[1:] + [None]:
        if d is None or (d - prev).days > 1:
            out.append(f"{start.day} {start:%b}" if start == prev else
                       (f"{start.day}–{prev.day} {prev:%b}" if start.month == prev.month
                        else f"{start.day} {start:%b} – {prev.day} {prev:%b}"))
            start = d
        prev = d if d is not None else prev
    return ", ".join(out)


def overall(days: pd.DataFrame) -> str:
    share = days.Verdict.value_counts(normalize=True)
    if share.get("Skip", 0) >= 0.5:
        return "Skip"
    if share.get("Go", 0) >= 0.5:
        return "Go"
    return "Okay"


def month_days(m: int, y: int):
    s = max(date(y, m, 1), TODAY)
    e = min((pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).date(), END)
    return build_days(s, e) if s <= e else None


def next_months(n=12):
    out = []
    for i in range(n):
        m = (TODAY.month - 1 + i) % 12 + 1
        y = TODAY.year + (TODAY.month - 1 + i) // 12
        if date(y, m, 1) > END:
            break
        out.append((m, y))
    return out


# ------------------------------------------------------------------------- calendar component
def months_between(a, b):
    out, d = [], date(a.year, a.month, 1)
    while d <= b:
        out.append((d.month, d.year))
        d = (pd.Timestamp(d) + pd.offsets.MonthBegin(1)).date()
    return out


def _day_labels(ev):
    names = list(dict.fromkeys(SHORT.get(e, e) for e in ev if e not in LONG))
    if len(names) > 2:
        names = names[:1] + [f"+{len(names) - 1} more"]
    return "".join(f'<span class="e">{esc(n)}</span>' for n in names)


def calendar_html(months, days: pd.DataFrame, focus=None, picks=None) -> str:
    """Month grids. focus=(start, end) dims days outside it; picks=[(start, end), ...] numbers and outlines them."""
    pick_of = {}
    for i, (s, e) in enumerate(picks or [], 1):
        for d in pd.date_range(s, e):
            pick_of[d] = i
    blocks = []
    for m, y in months:
        first = date(y, m, 1)
        last = (pd.Timestamp(first) + pd.offsets.MonthEnd(0)).date()
        a_, b_ = first, last
        if focus is not None:                     # only the weeks that hold the chosen dates
            a_ = max(first, focus[0] - timedelta(days=focus[0].weekday()))
            b_ = min(last, focus[1] + timedelta(days=6 - focus[1].weekday()))
        cells = [f'<span class="hd">{h}</span>' for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
        cells += ['<span></span>'] * a_.weekday()
        shown = []
        for dd in pd.date_range(a_, b_):
            d, k = dd, dd.day
            if d.date() < TODAY or d not in days.index:
                cells.append(f'<div class="adh-cell off"><span class="n">{k}</span></div>')
                continue
            r = days.loc[d]
            inside = (focus is None or focus[0] <= d.date() <= focus[1]) and (picks is None or d in pick_of)
            if not inside:
                cells.append(f'<div class="adh-cell dim" title="{esc(r.Reason)}"><span class="n">{k}</span></div>')
                continue
            shown.append(d)
            cls = f"adh-cell st-{r.Verdict}" + (" today" if d.date() == TODAY else "") + (" pick" if d in pick_of else "")
            badge = (f'<span class="badge">{pick_of[d]}</span>'
                     if d in pick_of and (d - pd.Timedelta(days=1)) not in pick_of else "")
            tip = esc(f"{d:%a %d %b} · {r.Verdict} · {r.Reason}")
            cells.append(f'<div class="{cls}" title="{tip}"><span class="n">{k}</span>{badge}{_day_labels(r.Events)}</div>')
        # this month's events, written out in full under the grid
        sub = days.loc[shown] if shown else days.iloc[0:0]
        evs = event_names(sub) if len(sub) else []
        lst = "".join(f"<li><b>{spans(sub, n)}</b> · {esc(n)}</li>" for n in evs)
        blocks.append(f'<div class="adh-month"><h4>{MONTHS[m-1]} {y}</h4><div class="adh-grid">{"".join(cells)}</div>'
                      + (f'<ul class="adh-mev">{lst}</ul>' if lst else "") + '</div>')
    return '<div class="adh-months">' + "".join(blocks) + '</div>'


# ------------------------------------------------------------------------- page
style.apply()
st.title("Plan your Abu Dhabi trip", anchor=False)
LEGEND = ('<div class="adh-legend">'
          f'<span>{dot("Go")}<b>Go</b> · quiet and comfortable</span>'
          f'<span>{dot("Okay")}<b>Okay</b> · a bit busy or warm</span>'
          f'<span>{dot("Skip")}<b>Skip</b> · busy and hot, or over 40°C</span></div>')
st.markdown(LEGEND, unsafe_allow_html=True)
st.caption(":material/info: Estimates only – crowds, weather and event dates may not be fully accurate")

tab_dates, tab_sugg, tab_cal, tab_best, tab_ask = st.tabs(
    [":material/event: Check my dates", ":material/route: Trip suggester", ":material/calendar_month: Calendar",
     ":material/wb_sunny: Best times", ":material/chat_bubble: Ask a question"])

# Trip suggester: show a words-only flight tip for the home country (no numbers).
# Set to False to hide it if DCT flight data should not be used on the public side.
SHOW_FLIGHT_TIP = True


@st.cache_data
def flight_months():
    """Per departure country: months when flights to Abu Dhabi are usually emptiest / fullest."""
    try:
        f = pd.read_csv(DATA / "flight_country_monthly.csv")
    except Exception:
        return {}
    f = f[f.Month.str[:4].astype(int) >= 2023]
    f["M"] = f.Month.str[5:7].astype(int)
    out = {}
    for c, g in f.groupby("Country"):
        if g.Seats.sum() / g.Month.nunique() < 3000:   # too few flights to say anything
            continue
        lf = g.groupby("M").PAX.sum() / g.groupby("M").Seats.sum()
        if len(lf) >= 10:
            out[c] = (lf.nsmallest(3).index.tolist(), lf.nlargest(3).index.tolist())
    return out


def suggest_windows(month: int, nights: int, top: int = 3):
    y = TODAY.year if month >= TODAY.month else TODAY.year + 1
    first = date(y, month, 1)
    if first > END:
        return y, []
    mend = (pd.Timestamp(first) + pd.offsets.MonthEnd(0)).date()
    lo = max(first - timedelta(days=5), TODAY + timedelta(days=1))
    hi = min(mend, END - timedelta(days=nights - 1))
    if lo > hi:
        return y, []
    days = build_days(lo, hi + timedelta(days=nights - 1))
    pts = (days.Verdict.map({"Go": 0, "Okay": 1, "Skip": 2}) + days.Busy.map({"Quiet": 0, "Average": 0.3, "Busy": 0.6})
           + days.Major * 0.8)   # big holidays/events that fill hotels count against a window
    cands = []
    for s in pd.date_range(lo, hi):
        w = days.loc[s: s + pd.Timedelta(days=nights - 1)]
        cands.append((pts.loc[w.index].mean() + abs((s.date() - first).days) * 0.002, s, w))
    cands.sort(key=lambda c: c[0])
    picks = []
    for sc, s, w in cands:
        if all(abs((s - p[1]).days) >= max(3, nights) for p in picks):
            picks.append((sc, s, w))
        if len(picks) == top:
            break
    return y, sorted([(s, w) for _, s, w in picks], key=lambda p: p[0])


def window_reason(w: pd.DataFrame) -> str:
    busy = w.Busy.value_counts(normalize=True)
    crowd = ("mostly quiet" if busy.get("Quiet", 0) >= 0.5 else
             "some busy days" if busy.get("Busy", 0) >= 0.3 else "normal crowds")
    hi = f"{w.High.min()}°C" if w.High.min() == w.High.max() else f"{w.High.min()}–{w.High.max()}°C"
    ev = [n for n in event_names(w) if n not in LONG]
    sch = sorted({s for s in w.School if s})
    extra = ("includes " + ", ".join(ev)) if ev else (sch[0] + " (approx.)") if sch else "no major holidays"
    return f"{crowd.capitalize()}, highs {hi}, {extra}."

@st.cache_data
def all_countries():
    try:
        return [x.strip() for x in (DATA / "countries.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
    except Exception:
        return sorted(flight_months())


# 1. check my dates -----------------------------------------------------------------------
DEFAULT_TRIP = (TODAY + timedelta(days=7), TODAY + timedelta(days=11))
QUICK = ["This weekend", "Next week", "Next 2 weeks", "Next month"]


def _clamp(s, e):
    return max(s, TODAY), min(e, END)


def _range_for(kind):
    wd = TODAY.weekday()
    if kind == "This weekend":                  # coming Fri – Sun
        fri = TODAY + timedelta(days=(4 - wd) % 7)
        return fri, fri + timedelta(days=2)
    if kind == "Next week":                     # next Mon – Sun
        mon = TODAY + timedelta(days=7 - wd)
        return mon, mon + timedelta(days=6)
    if kind == "Next 2 weeks":
        return TODAY + timedelta(days=1), TODAY + timedelta(days=14)
    if kind == "Next month":
        first = (pd.Timestamp(TODAY) + pd.offsets.MonthBegin(1)).date()
        return first, (pd.Timestamp(first) + pd.offsets.MonthEnd(0)).date()
    return DEFAULT_TRIP


def _on_quick():
    k = st.session_state.get("quick")
    if k:
        st.session_state.trip = _clamp(*_range_for(k))


def _on_reset():
    st.session_state.quick = None
    st.session_state.trip = DEFAULT_TRIP


def _on_dates():
    st.session_state.quick = None


with tab_dates:
    if "trip" not in st.session_state:
        st.session_state.trip = DEFAULT_TRIP
    c1, c2, c3 = st.columns([3, 2, 0.6], vertical_alignment="bottom")
    c1.segmented_control("Quick pick", QUICK, key="quick", on_change=_on_quick)
    rng = c2.date_input("Or choose dates", key="trip", min_value=TODAY, max_value=END, format="DD/MM/YYYY",
                        on_change=_on_dates)
    c3.button("Reset", on_click=_on_reset, icon=":material/restart_alt:", type="tertiary")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        s, e = rng
        days = build_days(s, e)
        v = overall(days)
        msg = {"Go": "Mostly quiet with comfortable weather",
               "Okay": "Fine to go – expect some crowds or warm days",
               "Skip": "Consider other dates – busy and hot, or extremely hot"}[v]
        cnt = days.Verdict.value_counts()
        split = " · ".join(f"{cnt[k]} {k}" for k in ("Go", "Okay", "Skip") if k in cnt)
        src = ("live forecast" if (days.WeatherSource == "forecast").all() else
               "live, then typical" if (days.WeatherSource == "forecast").any() else "typical for the season")
        evs = [n for n in event_names(days) if n not in LONG]
        ev_sub = ", ".join(SHORT.get(n, n) for n in evs[:3]) + (f" +{len(evs) - 3}" if len(evs) > 3 else "")
        when = f"{s:%a %d %b}" if s == e else f"{s:%a %d %b} – {e:%a %d %b %Y}"
        st.markdown(
            '<div class="adh-summary">'
            f'<div><div class="word ink-{v}">{dot(v)}{v}</div><div class="msg">{msg}</div></div>'
            f'<div><div class="lab">Your dates</div><div class="val">{len(days)} days</div><div class="sub">{when}</div></div>'
            f'<div><div class="lab">Temperature</div><div class="val">{days.Low.min()}–{days.High.max()}°C</div>'
            f'<div class="sub">{src}</div></div>'
            f'<div><div class="lab">Days</div><div class="val">{split}</div>'
            f'<div class="sub">{"Events: " + ev_sub if evs else "No major events"}</div></div>'
            '</div>', unsafe_allow_html=True)
        st.markdown(calendar_html(months_between(s, e), days, focus=(s, e)), unsafe_allow_html=True)
        sch = list(dict.fromkeys(x for x in days.School if x))
        notes = [NOTES[n] for n in event_names(days)] + [NOTES[x] for x in sch]
        with st.expander("About these events"):
            st.markdown("\n".join(f"- {n}" for n in notes) if notes else "No holidays or events on these dates")
    else:
        st.info("Choose an end date too")

# 1b. trip suggester ------------------------------------------------------------------------
with tab_sugg:
    fm = flight_months()
    with st.form("suggester"):
        c = st.columns(3)
        home = c[0].selectbox("Home country", ["Prefer not to say"] + all_countries(),
                              help="Only used for a flight tip")
        pref = c[1].selectbox("Preferred month", MONTHS, index=TODAY.month % 12)
        nights = c[2].number_input("Trip length (nights)", 1, 21, 5)
        sent = st.form_submit_button("Suggest dates", type="primary")
    if sent or "sugg_shown" in st.session_state:
        st.session_state.sugg_shown = True
        m = MONTHS.index(pref) + 1
        y, wins = suggest_windows(m, int(nights))
        if not wins:
            st.warning("Planning is available up to the end of 2027 – pick another month")
        else:
            st.subheader(f"Best dates around {pref} {y}", anchor=False)
            picks = [(s.date(), (s + pd.Timedelta(days=int(nights) - 1)).date()) for s, _ in wins]
            lo_, hi_ = min(p_[0] for p_ in picks), max(p_[1] for p_ in picks)
            span_days = build_days(max(date(lo_.year, lo_.month, 1), TODAY),
                                   min((pd.Timestamp(hi_) + pd.offsets.MonthEnd(0)).date(), END))
            st.markdown(calendar_html(months_between(lo_, hi_), span_days, picks=picks, focus=(lo_, hi_)),
                        unsafe_allow_html=True)
            rows_ = []
            for i, ((s, w), (a_, b_)) in enumerate(zip(wins, picks), 1):
                v = overall(w)
                rows_.append(f'<li><span class="badge-n">{i}</span>{dot(v)}<b>{a_:%a %d %b} – {b_:%a %d %b}</b>'
                             f' · {esc(window_reason(w))}</li>')
            st.markdown('<ul class="adh-picks">' + "".join(rows_) + '</ul>', unsafe_allow_html=True)
            if all(overall(w) == "Skip" for _, w in wins):
                st.info("This month is busy or very hot. See Best times for better months")
            if SHOW_FLIGHT_TIP and home in fm:
                empt, full = fm[home]
                name = lambda ms: ", ".join(MONTHS[x - 1] for x in sorted(ms))
                tip = f":material/flight: Flights from **{home}** are usually emptiest in {name(empt)} and fullest in {name(full)} (past years)"
                if m in full:
                    tip += f". {pref} is a full month – book flights early"
                st.markdown(tip)

# 2. calendar -----------------------------------------------------------------------------
with tab_cal:
    n = st.segmented_control("Show", [3, 6, 9, 12], default=6, format_func=lambda x: f"{x} months",
                             key="cal_n") or 6
    months = next_months(n)
    last_m, last_y = months[-1]
    end = min((pd.Timestamp(last_y, last_m, 1) + pd.offsets.MonthEnd(0)).date(), END)
    cal = build_days(TODAY, end)
    st.caption("Point at a day for details")
    st.markdown(calendar_html(months, cal), unsafe_allow_html=True)

# 3. best times ---------------------------------------------------------------------------
with tab_best:
    NEXT = TODAY.year + 1
    rows = []
    for m in range(1, 13):
        md = month_days(m, NEXT)
        if md is None:
            continue
        names = event_names(md)
        big = [n for n in names if n in MAJOR]
        rows.append({"Month": f"{MONTHS[m-1]} {NEXT}", "M": m, "Verdict": overall(md),
                     "Go": md.Verdict.eq("Go").mean(), "High": int(round(md.High.mean())),
                     "Big": big, "Events": ", ".join(dict.fromkeys(SHORT.get(n, n) for n in names)) or "—"})
    bt = pd.DataFrame(rows)
    # best = coolest weather first; months packed with big events (3 or more) are left out
    best = bt[bt.Big.map(len) < 3].sort_values(["High", "Go"], ascending=[True, False]).head(3)
    st.subheader(f"Best months in {NEXT}", anchor=False)
    for r in best.itertuples():
        why = f"about {r.High}°C, pleasant weather"
        if r.Big:
            why += f"; busy during {', '.join(SHORT.get(b, b) for b in r.Big)} – book early"
        st.markdown(f"{ICON[r.Verdict]}<b>{r.Month}</b> · {why}", unsafe_allow_html=True)
    crowded = bt[bt.Big.map(len) >= 3]
    for r in crowded.itertuples():
        st.info(f"**{r.Month}** also has good weather (about {r.High}°C), but {', '.join(SHORT.get(b, b) for b in r.Big)} "
                "make it one of the busiest months")
    st.subheader(f"Month by month, {NEXT}", anchor=False)
    tbl = (bt.assign(High=bt.High.map(lambda x: f"{x}°C"))[["Month", "Verdict", "High", "Events"]]
             .rename(columns={"High": "Typical high"}))
    _k = {"Go": "go", "Okay": "ok", "Skip": "sk"}
    style.table(tbl.style.map(lambda v: f"background-color:var(--{_k[v]}-tint);color:var(--{_k[v]}-ink)",
                              subset=["Verdict"]))

# 4. ask -----------------------------------------------------------------------------------
def answer(q: str) -> str:
    t = q.lower()
    month = next((i + 1 for i, m in enumerate(MONTHS) if m.lower() in t or re.search(rf"\b{m[:3].lower()}\b", t)), None)
    if any(k in t for k in ["price", "cheap", "cost", "fare", "expensive", "ticket"]):
        return "I can't see prices. Quieter (Go) dates are often easier to book, but that's not guaranteed."
    if month:
        y = TODAY.year if month >= TODAY.month else TODAY.year + 1
        md = month_days(month, y)
        if md is None:
            return "I can only plan up to the end of 2027."
        v = overall(md)
        evs = event_names(md)
        return (f"{ICON[v]} **{MONTHS[month-1]} {y}: {v}.** Typical highs around {int(md.High.mean())}°C. "
                f"{md.Verdict.eq('Go').mean():.0%} of days are a Go and {md.Busy.eq('Busy').mean():.0%} are busy. "
                + (f"Includes: {', '.join(evs)}." if evs else "No major holidays."))
    if "ramadan" in t or "eid" in t:
        return ("**Ramadan** (about 18 Feb – 19 Mar 2026 and 8 Feb – 9 Mar 2027) is usually calmer in hotels. "
                "**Eid** holidays right after are busy. Dates depend on the moon, so they can move by a day or two.")
    if any(k in t for k in ["f1", "grand prix", "formula"]):
        return ("The **Abu Dhabi Grand Prix** is 3–6 Dec 2026 and 10–12 Dec 2027. Hotels are busy, especially around "
                "Yas Island – book early or pick another week.")
    if any(k in t for k in ["event", "festival", "what's on", "whats on", "happening"]):
        up = build_days(TODAY, min(TODAY + timedelta(days=90), END))
        names = event_names(up)
        if not names:
            return "No major events in the next 3 months."
        return "Coming up in the next 3 months: " + "; ".join(
            f"**{n}** (from {min(d for d, e in up.Events.items() if n in e):%d %b})" for n in names) + "."
    if any(k in t for k in ["weather", "hot", "temperature", "cool", "heat"]):
        return ("Most pleasant: **November to March** (about 24–31°C). June to September is very hot (40°C+). "
                "Check my dates shows the live forecast for the next 2 weeks.")
    if any(k in t for k in ["crowd", "busy", "quiet", "peak", "avoid"]):
        return ("Usually quieter: **Ramadan and the summer months**, and Sundays. Busier: **Eid, National Day, "
                "the F1 weekend, New Year** and Fri–Sat weekends. Use the Calendar tab for exact days.")
    good = best.Month.tolist() if len(best) else []
    return ("Best months next year for pleasant weather: **" + ", ".join(good) + "**. "
            "December is lovely too but very busy (National Day, F1, New Year). "
            "Ask me about a month (\"How is March?\"), events, Ramadan, the F1, crowds or weather.")


with tab_ask:
    st.caption("Try: Best time to visit? · How is March? · What's on? · Is December busy?")
    if "chat" not in st.session_state:
        st.session_state.chat = [("assistant", "Ask me when to visit Abu Dhabi")]
    box = st.container()
    q = st.chat_input("Type your question")
    if q:
        st.session_state.chat += [("user", q), ("assistant", answer(q))]
    with box:
        for role, msg in st.session_state.chat:
            st.chat_message(role).markdown(msg, unsafe_allow_html=True)

st.caption("Weather data: Open-Meteo")
