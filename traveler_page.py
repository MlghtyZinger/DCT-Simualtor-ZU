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

from calendar_ad import NOTES, LAST_DAY

DATA = Path(__file__).parent / "data"
LAT, LON = 24.45, 54.38  # Abu Dhabi
TODAY = date.today()
END = LAST_DAY.date()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
COLOR = {"Go": "#2f9e44", "Okay": "#f2c12e", "Skip": "#e03131"}
ICON = {"Go": "🟢", "Okay": "🟡", "Skip": "🔴"}
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
    elif r.School:
        parts.append(r.School + " (approx.)")
    return " · ".join(parts)


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


# ------------------------------------------------------------------------- page
st.title("🧳 Plan your Abu Dhabi trip")
st.caption("🟢 **Go** – quiet and comfortable · 🟡 **Okay** – a bit busy or warm · 🔴 **Skip** – busy and hot, or over 40°C")

tab_dates, tab_sugg, tab_cal, tab_best, tab_ask = st.tabs(
    ["📅 Check my dates", "🎯 Trip suggester", "🗓️ Calendar", "⭐ Best times", "💬 Ask a question"])

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
    busy_events = {"Eid al-Fitr", "Eid al-Adha", "UAE National Day", "Abu Dhabi Grand Prix (F1)", "New Year"}
    pts = (days.Verdict.map({"Go": 0, "Okay": 1, "Skip": 2}) + days.Busy.map({"Quiet": 0, "Average": 0.3, "Busy": 0.6})
           + days.Event.isin(busy_events) * 0.8)   # crowded holidays count against a window
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
    ev = sorted({e for e in w.Event if e})
    sch = sorted({s for s in w.School if s})
    extra = ("includes " + ", ".join(ev)) if ev else (sch[0] + " (approx.)") if sch else "no major holidays"
    return f"{crowd.capitalize()}, highs {hi}, {extra}."

# 1. check my dates -----------------------------------------------------------------------
with tab_dates:
    s0 = TODAY + timedelta(days=7)
    rng = st.date_input("When are you travelling?", (s0, s0 + timedelta(days=4)),
                        min_value=TODAY, max_value=END, format="DD/MM/YYYY")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        days = build_days(*rng)
        v = overall(days)
        msg = {"Go": "Great choice – mostly quiet with comfortable weather.",
               "Okay": "Fine to go – expect some crowds or warm days.",
               "Skip": "Consider other dates – it will be busy and hot, or extremely hot."}[v]
        st.markdown(f"## {ICON[v]} {v}\n{msg}")
        st.markdown(f"Weather: **{days.Low.min()}–{days.High.max()}°C**"
                    + (" (live forecast)" if (days.WeatherSource == "forecast").all() else
                       " (live forecast for the next 2 weeks, typical weather after)"
                       if (days.WeatherSource == "forecast").any() else " (typical for this time of year)"))
        notes = sorted({n for n in list(days.Event) + list(days.School) if n})
        for n in notes:
            st.info(NOTES[n])
        strip = go.Figure(go.Bar(x=days.index, y=[1] * len(days), marker_color=days.Verdict.map(COLOR),
                                 customdata=days[["Verdict", "Reason"]],
                                 hovertemplate="%{x|%a %d %b}<br><b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"))
        strip.update_layout(height=140, margin=dict(t=5, b=5, l=5, r=5), yaxis_visible=False,
                            bargap=0.08, xaxis=dict(tickformat="%a %d %b", dtick=86400000.0 if len(days) <= 21 else 7 * 86400000.0))
        st.plotly_chart(strip, width="stretch")
        st.caption("Hover a day for details.")
    else:
        st.info("Pick a start date and an end date.")

# 1b. trip suggester ------------------------------------------------------------------------
with tab_sugg:
    st.markdown("Tell us a little about your trip and we'll suggest the best dates.")
    fm = flight_months()
    with st.form("suggester"):
        c = st.columns(3)
        home = c[0].selectbox("Home country", ["Other / prefer not to say"] + sorted(fm),
                              help="Used only to add a tip about flights from your country.")
        pref = c[1].selectbox("Preferred month", MONTHS, index=TODAY.month % 12)
        nights = c[2].number_input("Trip length (nights)", 1, 21, 5)
        sent = st.form_submit_button("Suggest dates", type="primary")
    if sent or "sugg_shown" in st.session_state:
        st.session_state.sugg_shown = True
        m = MONTHS.index(pref) + 1
        y, wins = suggest_windows(m, int(nights))
        if not wins:
            st.warning("I can only plan up to the end of 2027 – please pick another month.")
        else:
            st.markdown(f"### Best dates around {pref} {y}")
            for i, (s, w) in enumerate(wins, 1):
                v = overall(w)
                e = s + pd.Timedelta(days=int(nights) - 1)
                st.markdown(f"**{i}. {ICON[v]} {s:%a %d %b} → {e:%a %d %b %Y}** — {window_reason(w)}")
            if all(overall(w) == "Skip" for _, w in wins):
                st.info("This month is busy and/or very hot. See ⭐ Best times for better months.")
            if SHOW_FLIGHT_TIP and home in fm:
                empt, full = fm[home]
                name = lambda ms: ", ".join(MONTHS[x - 1] for x in sorted(ms))
                tip = f"✈️ Flights from **{home}** are usually emptiest in {name(empt)} and fullest in {name(full)} (past years)."
                if m in full:
                    tip += f" {pref} is a full month – book flights early."
                st.markdown(tip)
            st.caption("Suggestions are based on our crowd forecast and the weather – a guide, not a guarantee. "
                       "No prices are included.")

# 2. calendar -----------------------------------------------------------------------------
with tab_cal:
    n = st.select_slider("Show", options=[3, 6, 9, 12], value=6, format_func=lambda x: f"{x} months")
    end = min((pd.Timestamp(TODAY) + pd.DateOffset(months=n)).date(), END)
    cal = build_days(TODAY, end)
    cal["dow"] = cal.index.dayofweek
    cal["week"] = cal.index - pd.to_timedelta(cal.dow, unit="D")
    weeks = sorted(cal.week.unique())
    code = {"Go": 0, "Okay": 1, "Skip": 2}
    z = [[None] * len(weeks) for _ in range(7)]
    txt = [[""] * len(weeks) for _ in range(7)]
    for d, r in cal.iterrows():
        j = weeks.index(r.week)
        z[r.dow][j] = code[r.Verdict]
        txt[r.dow][j] = f"{d:%a %d %b %Y}<br><b>{ICON[r.Verdict]} {r.Verdict}</b><br>{r.Reason}"
    fig = go.Figure(go.Heatmap(
        z=z, x=weeks, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], text=txt,
        hovertemplate="%{text}<extra></extra>", xgap=3, ygap=3, zmin=0, zmax=2, showscale=False,
        colorscale=[[0, COLOR["Go"]], [0.33, COLOR["Go"]], [0.34, COLOR["Okay"]], [0.66, COLOR["Okay"]],
                    [0.67, COLOR["Skip"]], [1, COLOR["Skip"]]]))
    fig.update_layout(height=300, margin=dict(t=10, b=10), yaxis_autorange="reversed",
                      xaxis=dict(tickformat="%d %b", title="Week starting"))
    st.plotly_chart(fig, width="stretch")
    st.caption("🟢 Go · 🟡 Okay · 🔴 Skip — hover a day to see why.")
    ev = cal[cal.Event != ""].groupby("Event").apply(lambda g: (g.index.min(), g.index.max()))
    if len(ev):
        st.markdown("**Holidays and events in this period**")
        for name, (a, b) in sorted(ev.items(), key=lambda x: x[1][0]):
            when = f"{a:%d %b}" + ("" if a == b else f" – {b:%d %b %Y}")
            st.markdown(f"- **{when}:** {NOTES[name]}")

# 3. best times ---------------------------------------------------------------------------
with tab_best:
    rows = []
    for m, y in next_months(12):
        md = month_days(m, y)
        if md is None:
            continue
        vc = md.Verdict.value_counts(normalize=True)
        rows.append({"Month": f"{MONTHS[m-1]} {y}", "Verdict": overall(md), "Go": vc.get("Go", 0),
                     "High": int(md.High.mean()),
                     "Events": ", ".join(sorted({e for e in md.Event if e})) or "—"})
    bt = pd.DataFrame(rows)
    best = bt.sort_values("Go", ascending=False).head(3)
    st.markdown("### Best months in the next year")
    for r in best.itertuples():
        st.markdown(f"{ICON[r.Verdict]} **{r.Month}** – about {r.High}°C, {r.Go:.0%} of days are a Go")
    st.markdown("### Month by month")
    st.dataframe(bt.assign(Verdict=bt.Verdict.map(lambda v: f"{ICON[v]} {v}"),
                           High=bt.High.map(lambda x: f"{x}°C"))[["Month", "Verdict", "High", "Events"]]
                 .rename(columns={"High": "Typical high"}), hide_index=True, width="stretch")

# 4. ask -----------------------------------------------------------------------------------
def answer(q: str) -> str:
    t = q.lower()
    month = next((i + 1 for i, m in enumerate(MONTHS) if m.lower() in t or re.search(rf"\b{m[:3].lower()}\b", t)), None)
    if any(k in t for k in ["price", "cheap", "cost", "fare", "expensive", "ticket"]):
        return "I can't see prices. Quieter (🟢) dates are often easier to book, but that's not guaranteed."
    if month:
        y = TODAY.year if month >= TODAY.month else TODAY.year + 1
        md = month_days(month, y)
        if md is None:
            return "I can only plan up to the end of 2027."
        v = overall(md)
        evs = sorted({e for e in md.Event if e})
        return (f"{ICON[v]} **{MONTHS[month-1]} {y}: {v}.** Typical highs around {int(md.High.mean())}°C. "
                f"{md.Verdict.eq('Go').mean():.0%} of days are a Go and {md.Busy.eq('Busy').mean():.0%} are busy. "
                + (f"Includes: {', '.join(evs)}." if evs else "No major holidays."))
    if "ramadan" in t or "eid" in t:
        return ("**Ramadan** (about 18 Feb – 19 Mar 2026 and 8 Feb – 9 Mar 2027) is usually calmer in hotels. "
                "**Eid** holidays right after are busy. Dates depend on the moon, so they can move by a day or two.")
    if any(k in t for k in ["f1", "grand prix", "formula"]):
        return "The **Abu Dhabi Grand Prix** is 4–6 Dec 2026. Hotels are busy, especially around Yas Island – book early or pick another week."
    if any(k in t for k in ["weather", "hot", "temperature", "cool", "heat"]):
        return ("Most pleasant: **November to March** (about 24–31°C). June to September is very hot (40°C+). "
                "Check my dates shows the live forecast for the next 2 weeks.")
    if any(k in t for k in ["crowd", "busy", "quiet", "peak", "avoid"]):
        return ("Usually quieter: **Ramadan and the summer months**, and Sundays. Busier: **Eid, National Day, "
                "the F1 weekend, New Year** and Fri–Sat weekends. Use the Calendar tab for exact days.")
    good = pd.DataFrame(rows).sort_values("Go", ascending=False).head(3).Month.tolist() if rows else []
    return ("Best balance of quiet and good weather in the next year: **" + ", ".join(good) + "**. "
            "Ask me about a month (\"How is March?\"), Ramadan, the F1, crowds or weather.")


with tab_ask:
    st.caption("Simple answers from our forecast and the weather. Try: *When is the best time to visit?* · "
               "*How is March?* · *Will it be crowded in December?* · *Ramadan* · *Weather*")
    if "chat" not in st.session_state:
        st.session_state.chat = [("assistant", "Hi! Ask me when to visit Abu Dhabi.")]
    box = st.container()
    q = st.chat_input("Type your question")
    if q:
        st.session_state.chat += [("user", q), ("assistant", answer(q))]
    with box:
        for role, msg in st.session_state.chat:
            st.chat_message(role).markdown(msg)

st.caption("Crowd levels: our LightGBM forecast from Abu Dhabi hotel history and holiday calendars – a guide, not a "
           "guarantee. Weather: Open-Meteo. Ramadan/Eid dates are approximate; school holidays are approximate.")
