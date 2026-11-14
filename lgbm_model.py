"""The ONE LightGBM model used by the traveler page and the admin dashboard.
Uses only things known ahead of time (calendar, weekends, holidays, events) + a straight-line
growth trend, so it can forecast future dates.  LightGBM learns how each day differs from the trend.
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
from calendar_ad import features

PARAMS = dict(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10,
              subsample=0.9, subsample_freq=1, colsample_bytree=0.9, verbose=-1, random_state=1)
ORIGIN = pd.Timestamp("2022-01-01")


def _t(idx):
    return np.asarray((pd.DatetimeIndex(idx) - ORIGIN).days, dtype=float)


def _X(idx):
    return features(idx).drop(columns="year")


def fit_predict(train: pd.Series, horizon, relative: bool = False) -> pd.Series:
    """Fit on a daily series (index = dates) and predict the dates in `horizon`.
    relative=True returns how busy each day is compared with the growth trend (1.0 = normal)."""
    a, b = np.polyfit(_t(train.index), train.values, 1)          # growth trend
    ratio = train.values / (a * _t(train.index) + b)               # day vs trend
    m = lgb.LGBMRegressor(**PARAMS).fit(_X(train.index), ratio)
    horizon = pd.DatetimeIndex(horizon)
    rel = m.predict(_X(horizon))
    return pd.Series(rel if relative else rel * (a * _t(horizon) + b), index=horizon)
