"""Builds the admin-only tables.
Run:  python prep_admin.py data_international_train.xlsx flight_data_working.xlsx
  -> data/flight_country_monthly.csv   flight seats/passengers by departure country and month
  -> data/nationality_profile.csv      hotel nights + arrivals by nationality, year, month
  -> data/lgbm_forecast.csv            LightGBM daily guests: history + forecast to Dec 2027
  -> data/model_compare.csv            backtest Jan-Jul 2025: actual vs LightGBM vs Prophet vs last year
  -> data/model_compare_metrics.csv    errors of the three methods
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from calendar_ad import EVENTS, LAST_DAY
from lgbm_model import fit_predict

DATA = Path(__file__).parent / "data"
tr_xlsx, fl_xlsx = sys.argv[1], sys.argv[2]

# ---- flights + nationalities ------------------------------------------------------------
c = pd.read_excel(fl_xlsx, "Flight_By_Country").rename(columns={
    "Departure Country": "Country", "Total PAX": "PAX", "Total Seats": "Seats", "Total P2P": "P2P"})
c[["Month", "Country", "Seats", "PAX", "P2P", "Routes"]].to_csv(DATA / "flight_country_monthly.csv", index=False)
t = pd.read_excel(tr_xlsx)
t["Date"] = pd.to_datetime(t["Date"])
n = (t.assign(Y=t.Date.dt.year, M=t.Date.dt.month)
       .groupby(["Nationality", "Y", "M"]).agg(Nights=("Guests", "sum"), Arrivals=("New Arrivals", "sum")).reset_index())
n.to_csv(DATA / "nationality_profile.csv", index=False)

# ---- models -------------------------------------------------------------------------------
d = pd.read_csv(DATA / "daily_guests.csv", parse_dates=["Date"])
d = d[d.Source == "Actual"].set_index("Date")
y = (d.International + d.Domestic).rename("y")
tr, te = y.index < "2025-01-01", y.index >= "2025-01-01"


def prophet_fit(train: pd.Series, horizon: pd.DatetimeIndex) -> pd.Series:
    from prophet import Prophet
    hol = pd.DataFrame([{"holiday": k, "ds": dd} for k, spans in EVENTS.items() for s, e in spans
                        for dd in pd.date_range(s, e)])
    m = Prophet(holidays=hol, yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False,
                seasonality_mode="multiplicative", changepoint_prior_scale=0.05)
    m.fit(pd.DataFrame({"ds": train.index, "y": train.values}))
    return pd.Series(m.predict(pd.DataFrame({"ds": horizon})).yhat.values, index=horizon)


lg_bt = fit_predict(y[tr], y.index[te])
pr_bt = prophet_fit(y[tr], y.index[te])
ly = y.shift(364)[te]
cmp_ = pd.DataFrame({"Date": y.index[te], "Actual": y[te].values, "LightGBM": lg_bt.values,
                     "Prophet": pr_bt.values, "Same day last year": ly.values})
cmp_.round({"Actual": 0, "LightGBM": 0, "Prophet": 0, "Same day last year": 0}).to_csv(DATA / "model_compare.csv", index=False)
wm = lambda a, b: float(np.abs(a - b).sum() / a.sum() * 100)
mon = lambda s: s.resample("MS").mean()
cm = cmp_.set_index("Date")
rows = []
for k in ["LightGBM", "Prophet", "Same day last year"]:
    rows.append({"Method": k, "Daily error %": wm(cm.Actual, cm[k]),
                 "Weekly error %": wm(cm.Actual.resample("W-MON").mean(), cm[k].resample("W-MON").mean()),
                 "Monthly error %": wm(mon(cm.Actual), mon(cm[k]))})
met = pd.DataFrame(rows).round(1)
met.to_csv(DATA / "model_compare_metrics.csv", index=False)
print(met.to_string(index=False))

# ---- final forecasts to Dec 2027 ------------------------------------------------------------
fut = pd.date_range(y.index.max() + pd.Timedelta(days=1), LAST_DAY)
lg_f = fit_predict(y, fut).values
pr_f = prophet_fit(y, fut)
out = pd.concat([
    pd.DataFrame({"Date": y.index, "Guests": y.values, "Type": "Actual"}),
    pd.DataFrame({"Date": fut, "Guests": lg_f, "Type": "LightGBM forecast"}),
    pd.DataFrame({"Date": fut, "Guests": pr_f.values, "Type": "Prophet forecast"}),
])
out.round({"Guests": 0}).to_csv(DATA / "lgbm_forecast.csv", index=False)
print(out.groupby("Type").Guests.mean().round(0))
