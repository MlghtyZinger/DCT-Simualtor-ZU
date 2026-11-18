"""Admin-only tabs: LightGBM forecast, LightGBM vs Prophet, flight fullness, visitor profiles."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import style

DATA = Path(__file__).parent / "data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
C = {"Actual": style.INK, "LightGBM": style.ACCENT, "Prophet": "#9A8F80", "Same day last year": "#CFC8BC"}


@st.cache_data
def _load():
    fc = pd.read_csv(DATA / "lgbm_forecast.csv", parse_dates=["Date"])
    cmp_ = pd.read_csv(DATA / "model_compare.csv", parse_dates=["Date"]).set_index("Date")
    met = pd.read_csv(DATA / "model_compare_metrics.csv")
    fl = pd.read_csv(DATA / "flight_country_monthly.csv")
    fl["Y"], fl["M"] = fl.Month.str[:4].astype(int), fl.Month.str[5:7].astype(int)
    nat = pd.read_csv(DATA / "nationality_profile.csv")
    return fc, cmp_, met, fl[fl.Y >= 2023], nat[nat.Y >= 2023]


def _agg(s: pd.Series, level: str) -> pd.Series:
    return s if level == "Daily" else s.resample("W-MON" if level == "Weekly" else "MS").mean()


# --------------------------------------------------------------------------------------------
def render_forecast():
    fc, _, met, _, _ = _load()
    st.subheader("Hotel guests forecast – LightGBM (main model)")
    st.caption("Total hotel guests per night (international + domestic). Actual to Jul 2025, LightGBM forecast to Dec 2027. "
               "The model uses only things known ahead of time: calendar, weekends, holidays, events and the growth trend. "
               "It assumes past growth continues, so 2027 values may be too high – use them for timing (which periods are busiest), not exact totals.")
    lg = met.set_index("Method").loc["LightGBM"]
    k = st.columns(3)
    k[0].metric("Daily error (Jan–Jul 2025 test)", f"{lg['Daily error %']}%")
    k[1].metric("Weekly error", f"{lg['Weekly error %']}%")
    k[2].metric("Monthly error", f"{lg['Monthly error %']}%")
    level = st.radio("View", ["Daily", "Weekly", "Monthly"], index=2, horizontal=True, key="lg_level")
    act = fc[fc.Type == "Actual"].set_index("Date").Guests
    lgf = fc[fc.Type == "LightGBM forecast"].set_index("Date").Guests
    fig = go.Figure()
    fig.add_scatter(x=_agg(act, level).index, y=_agg(act, level), name="Actual", line_color=C["Actual"])
    fig.add_scatter(x=_agg(lgf, level).index, y=_agg(lgf, level), name="LightGBM forecast", line_color=C["LightGBM"])
    fig.update_layout(height=380, margin=dict(t=10, b=10), yaxis_title="Guests per night",
                      legend=dict(orientation="h", y=1.08), hovermode="x unified")
    style.chart(fig)

    yr = st.selectbox("Busiest periods in", [2026, 2027], index=1, key="lg_year")
    s = lgf[lgf.index.year == yr]
    a, b, c = st.columns(3)
    a.markdown("**Top days**")
    style.table(a, s.nlargest(10).rename("Guests").reset_index().assign(Date=lambda d: d.Date.dt.strftime("%a %d %b"))
                .style.format({"Guests": "{:,.0f}"}))
    wk = s.resample("W-MON", label="left", closed="left").mean()
    b.markdown("**Top weeks** (week starting)")
    style.table(b, wk.nlargest(10).rename("Guests").reset_index().assign(Date=lambda d: d.Date.dt.strftime("%d %b"))
                .style.format({"Guests": "{:,.0f}"}))
    mo = s.resample("MS").mean()
    c.markdown("**Months, busiest first**")
    style.table(c, mo.sort_values(ascending=False).rename("Guests").reset_index()
                .assign(Date=lambda d: d.Date.dt.strftime("%B")).style.format({"Guests": "{:,.0f}"}))


# --------------------------------------------------------------------------------------------
def render_compare():
    fc, cmp_, met, _, _ = _load()
    st.subheader("LightGBM vs Prophet")
    m = met.set_index("Method")
    best = m["Daily error %"].idxmin()
    st.markdown(
        f"Both models were trained on Jan 2022 – Dec 2024 with the **same information** (calendar, weekends, holidays, "
        f"events) and tested on **Jan – Jul 2025**. Lower error is better. "
        f"On this test **{best}** was more accurate; both beat the simple *same day last year* guess.")
    style.table(met.style.format({c: "{:.1f}%" for c in met.columns if "%" in c})
                 .highlight_min(subset=[c for c in met.columns if "%" in c], props="font-weight:600;color:var(--accent)"))
    level = st.radio("View", ["Daily", "Weekly", "Monthly"], index=1, horizontal=True, key="cmp_level")
    fig = go.Figure()
    for col in ["Actual", "LightGBM", "Prophet", "Same day last year"]:
        s = _agg(cmp_[col], level)
        fig.add_scatter(x=s.index, y=s, name=col, line=dict(color=C[col], dash="dot" if col == "Same day last year" else None,
                                                             width=3 if col == "Actual" else 2))
    fig.update_layout(height=360, margin=dict(t=10, b=10), yaxis_title="Guests per night",
                      legend=dict(orientation="h", y=1.1), hovermode="x unified")
    style.chart(fig)

    st.markdown("**Forecasts to Dec 2027 (monthly average)**")
    fig2 = go.Figure()
    act = fc[fc.Type == "Actual"].set_index("Date").Guests.resample("MS").mean()
    fig2.add_scatter(x=act.index, y=act, name="Actual", line_color=C["Actual"])
    for t, col in [("LightGBM forecast", "LightGBM"), ("Prophet forecast", "Prophet")]:
        s = fc[fc.Type == t].set_index("Date").Guests.resample("MS").mean()
        fig2.add_scatter(x=s.index, y=s, name=t, line_color=C[col])
    fig2.update_layout(height=340, margin=dict(t=10, b=10), yaxis_title="Guests per night",
                       legend=dict(orientation="h", y=1.1), hovermode="x unified")
    style.chart(fig2)
    st.caption("Why LightGBM is the main model: it is the model the team built and tuned, it follows holidays and "
               "weekends closely, and with same-day arrivals it reaches about 3.5% daily error. Prophet is kept as a "
               "check. Both models carry the past growth trend forward, so forecasts far ahead may be too high.")


# --------------------------------------------------------------------------------------------
def render_flights():
    _, _, _, fl, _ = _load()
    st.subheader("Flight fullness by departure country")
    st.caption("Seats filled = passengers ÷ seats, all airlines, flights to Abu Dhabi, average of 2023 – Feb 2026. "
               "Historical only – the data has no fares or seat availability.")
    g = fl.groupby("Country").agg(Seats=("Seats", "sum"), PAX=("PAX", "sum"), Months=("Month", "nunique"))
    g["Seats filled"] = g.PAX / g.Seats
    g["Seats / month"] = g.Seats / g.Months
    countries = g.sort_values("Seats", ascending=False).index.tolist()
    ctry = st.selectbox("Country", countries, key="fl_country")
    c = fl[fl.Country == ctry].groupby("M").agg(Seats=("Seats", "sum"), PAX=("PAX", "sum"))
    c["LF"] = c.PAX / c.Seats
    c = c.reindex(range(1, 13))
    v = c.dropna()
    k = st.columns(3)
    k[0].metric("Emptiest month", f"{MONTHS[v.LF.idxmin()-1]} · {min(v.LF.min(), 1):.0%}")
    k[1].metric("Fullest month", f"{MONTHS[v.LF.idxmax()-1]} · {min(v.LF.max(), 1):.0%}")
    k[2].metric("Seats per month (avg)", f"{g.loc[ctry, 'Seats / month']:,.0f}")
    lf = c.LF.clip(upper=1)
    fig = go.Figure(go.Bar(x=MONTHS, y=lf * 100, customdata=c.Seats,
                           marker_color=[style.ACCENT if m == v.LF.idxmax() else style.NEUTRAL_SERIES for m in range(1, 13)],
                           hovertemplate="%{x}: %{y:.0f}% full<extra></extra>"))
    fig.update_layout(height=320, margin=dict(t=10, b=10), yaxis=dict(title="Seats filled (%)", range=[0, 105]))
    style.chart(fig)
    if (c.LF > 1).any():
        st.caption("Some months show more passengers than seats in the raw data; shown capped at 100%.")
    if g.loc[ctry, "Seats / month"] < 3000:
        st.warning("Few seats on this route – percentages jump around a lot.")
    st.markdown("**All countries**")
    style.table(g.sort_values("Seats", ascending=False)[["Seats / month", "Seats filled"]].reset_index()
                 .style.format({"Seats / month": "{:,.0f}", "Seats filled": "{:.0%}"}))


# --------------------------------------------------------------------------------------------
def render_profiles():
    _, _, _, _, nat = _load()
    st.subheader("Visitor profiles by nationality")
    st.caption("International hotel guests, 2023 – Jul 2025. Stay = hotel nights ÷ check-ins (approximate). "
               "Hotel guests only; nationality is not the same as the country flown from.")
    allstay = nat.Nights.sum() / nat.Arrivals.sum()
    tot = nat.groupby("Nationality").agg(Nights=("Nights", "sum"), Arrivals=("Arrivals", "sum"))
    tot["Avg stay (nights)"] = tot.Nights / tot.Arrivals
    tot["Share of nights"] = tot.Nights / tot.Nights.sum()
    bym = nat.groupby(["Nationality", "M"]).Nights.mean().unstack().fillna(0)
    tot["Top month"] = bym.idxmax(axis=1).map(lambda m: MONTHS[m - 1])
    tot["Quietest month"] = bym.idxmin(axis=1).map(lambda m: MONTHS[m - 1])
    names = tot.sort_values("Nights", ascending=False).index.tolist()
    who = st.selectbox("Nationality", names, format_func=str.title, key="pf_nat")
    r = tot.loc[who]
    k = st.columns(3)
    k[0].metric("Average stay", f"{r['Avg stay (nights)']:.1f} nights", f"{r['Avg stay (nights)'] - allstay:+.1f} vs all",
                delta_color="off")
    k[1].metric("Busiest month", r["Top month"])
    k[2].metric("Share of all international nights", f"{r['Share of nights']:.1%}")
    share = bym.loc[who] / bym.loc[who].sum()
    fig = go.Figure(go.Bar(x=MONTHS, y=share * 100, marker_color=[style.ACCENT if m == share.idxmax() else style.NEUTRAL_SERIES for m in range(1, 13)],
                           hovertemplate="%{x}: %{y:.1f}% of their nights<extra></extra>"))
    fig.update_layout(height=300, margin=dict(t=10, b=10), yaxis_title="% of their hotel nights")
    style.chart(fig)
    st.markdown("**All nationalities**")
    style.table(tot.sort_values("Nights", ascending=False)
                 [["Avg stay (nights)", "Share of nights", "Top month", "Quietest month"]].reset_index()
                 .assign(Nationality=lambda d: d.Nationality.str.title())
                 .style.format({"Avg stay (nights)": "{:.1f}", "Share of nights": "{:.1%}"}))
