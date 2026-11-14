"""Abu Dhabi event + holiday calendar (shared by the model and the traveler page).
Islamic dates are APPROXIMATE (moon sighting). School holidays are a rule of thumb, not official dates.
"""
import pandas as pd

EVENTS = {
    "Ramadan": [("2022-04-02", "2022-05-01"), ("2023-03-23", "2023-04-20"), ("2024-03-11", "2024-04-09"),
                ("2025-03-01", "2025-03-29"), ("2026-02-18", "2026-03-19"), ("2027-02-08", "2027-03-09")],
    "Eid al-Fitr": [("2022-05-02", "2022-05-05"), ("2023-04-21", "2023-04-24"), ("2024-04-10", "2024-04-14"),
                    ("2025-03-30", "2025-04-02"), ("2026-03-20", "2026-03-23"), ("2027-03-10", "2027-03-13")],
    "Eid al-Adha": [("2022-07-08", "2022-07-11"), ("2023-06-27", "2023-06-30"), ("2024-06-15", "2024-06-18"),
                    ("2025-06-05", "2025-06-08"), ("2026-05-26", "2026-05-29"), ("2027-05-16", "2027-05-19")],
    "UAE National Day": [(f"{y}-12-01", f"{y}-12-03") for y in range(2022, 2028)],
    "Abu Dhabi Grand Prix (F1)": [("2022-11-18", "2022-11-20"), ("2023-11-24", "2023-11-26"),
                                  ("2024-12-06", "2024-12-08"), ("2025-12-05", "2025-12-07"),
                                  ("2026-12-04", "2026-12-06"), ("2027-12-03", "2027-12-05")],
    "New Year": [(f"{y}-12-30", f"{y + 1}-01-02") for y in range(2021, 2028)],
}

NOTES = {
    "Ramadan": "Ramadan – hotels are usually calmer; some places change opening hours, evenings are lively.",
    "Eid al-Fitr": "Eid al-Fitr holiday – many visitors from the UAE and the region.",
    "Eid al-Adha": "Eid al-Adha holiday – many visitors from the UAE and the region.",
    "UAE National Day": "UAE National Day long weekend – celebrations and busy hotels.",
    "Abu Dhabi Grand Prix (F1)": "Abu Dhabi Grand Prix (F1) weekend – busy, especially around Yas Island; book early.",
    "New Year": "New Year period – busy, fireworks and events.",
    "winter school holiday": "School winter holiday (approx.) – families travel.",
    "spring school break": "School spring break (approx.) – families travel.",
    "summer school holiday": "School summer holiday (approx.) – many residents travel abroad.",
}

LAST_DAY = pd.Timestamp("2027-12-31")


def event_on(d):
    d = pd.Timestamp(d)
    for name, spans in EVENTS.items():
        for s, e in spans:
            if pd.Timestamp(s) <= d <= pd.Timestamp(e):
                return name
    return None


def school_break(d):
    d = pd.Timestamp(d)
    md = (d.month, d.day)
    if md >= (12, 15) or md <= (1, 5):
        return "winter school holiday"
    if (3, 25) <= md <= (4, 5):
        return "spring school break"
    if (7, 6) <= md <= (8, 29):
        return "summer school holiday"
    return None


def features(dates) -> pd.DataFrame:
    """Only things known ahead of time: calendar, weekends, holidays, events."""
    d = pd.DatetimeIndex(dates)
    f = pd.DataFrame(index=d)
    f["dow"] = d.dayofweek
    f["month"] = d.month
    f["doy"] = d.dayofyear
    f["year"] = d.year
    f["weekend"] = d.dayofweek.isin([4, 5]).astype(int)
    ev = [event_on(x) for x in d]
    for i, name in enumerate(EVENTS):
        f[f"ev_{i}"] = [int(e == name) for e in ev]
    sb = [school_break(x) for x in d]
    for k in ["winter", "spring", "summer"]:
        f["school_" + k] = [int(bool(s) and s.startswith(k)) for s in sb]
    return f
