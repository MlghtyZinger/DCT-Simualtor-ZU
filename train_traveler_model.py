"""Option A: LightGBM trained ONLY on things known ahead of time (calendar, weekends,
holidays, events) so it can forecast future dates for the traveler page.
Run:  python train_traveler_model.py      -> data/traveler_forecast.csv, data/traveler_model_check.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
sys.path.insert(0, str(Path(__file__).parent))
from calendar_ad import features, event_on, school_break, LAST_DAY

DATA = Path(__file__).parent / "data"
d = pd.read_csv(DATA / "daily_guests.csv", parse_dates=["Date"])
d = d[d.Source == "Actual"].set_index("Date")
y = (d.International + d.Domestic).rename("y")
X = features(y.index)
P = dict(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10,
         subsample=0.9, subsample_freq=1, colsample_bytree=0.9, verbose=-1, random_state=1)

# --- check: train to Dec 2024, test Jan–Jul 2025 ---------------------------------------
tr, te = y.index < "2025-01-01", y.index >= "2025-01-01"
m = lgb.LGBMRegressor(**P).fit(X[tr], y[tr])
pred = pd.Series(m.predict(X[te]), index=y.index[te])
last_year = y.shift(364)[te]
wm = lambda a, b: float(np.abs(a - b).sum() / a.sum() * 100)
yt = y[te]
mon = lambda s: s.resample("MS").mean()
check = pd.DataFrame({
    "Method": ["LightGBM (calendar + events only)", "Same day last year (simple guess)"],
    "Daily error %": [wm(yt, pred), wm(yt, last_year)],
    "Monthly error %": [wm(mon(yt), mon(pred)), wm(mon(yt), mon(last_year))],
}).round(1)
check.to_csv(DATA / "traveler_model_check.csv", index=False)
print(check.to_string(index=False))

# --- busy-level check: does it rank quiet vs busy days correctly? -----------------------
q = lambda s: pd.qcut(s.rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
print("level agreement test period:", round((q(pred) == q(yt)).mean() * 100, 1), "%")

# --- final model on all history, forecast ahead ------------------------------------------
m = lgb.LGBMRegressor(**P).fit(X, y)
fut = pd.date_range("2026-01-01", LAST_DAY)
f = pd.DataFrame({"Date": fut, "Pred": m.predict(features(fut))})
yr = f[f.Date.dt.year == 2027].Pred
lo, hi = yr.quantile(0.40), yr.quantile(0.75)
f["Busy"] = np.select([f.Pred < lo, f.Pred < hi], ["Quiet", "Average"], "Busy")
f["Event"] = [event_on(x) or "" for x in f.Date]
f["School"] = [school_break(x) or "" for x in f.Date]
f[["Date", "Busy", "Event", "School"]].to_csv(DATA / "traveler_forecast.csv", index=False)
print(f.groupby(f.Date.dt.month).Busy.agg(lambda s: s.value_counts().to_dict()).tail(12))
