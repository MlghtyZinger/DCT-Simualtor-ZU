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
                                  ("2026-12-03", "2026-12-06"), ("2027-12-10", "2027-12-12")],
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

# Other Abu Dhabi events (shown to travelers; NOT used to train the model – no past dates).
# Dates from official announcements / press, checked Nov 2026 – see SOURCES below.
EXTRA_EVENTS = {
    "Abu Dhabi Festival": [("2026-11-18", "2026-12-19")],
    "Frieze Abu Dhabi (art fair)": [("2026-11-19", "2026-11-22")],
    "Mother of the Nation Festival": [("2026-11-28", "2026-12-02"), ("2026-12-09", "2027-01-03")],
    "Culture Summit Abu Dhabi": [("2026-12-08", "2026-12-10")],
    "Guggenheim Abu Dhabi opening": [("2026-12-11", "2026-12-11")],
    "Liwa International Festival": [("2026-12-11", "2027-01-02")],
    "IDEX & NAVDEX (defence exhibition)": [("2027-01-21", "2027-01-25")],
    "Mubadala Abu Dhabi Open (tennis)": [("2027-01-31", "2027-02-06")],
    "Abu Dhabi International Book Fair": [("2027-04-24", "2027-05-03")],
    "ADIPEC (energy exhibition)": [("2027-11-01", "2027-11-04")],
    "Abu Dhabi Championship (golf)": [("2027-11-04", "2027-11-07")],
}
NOTES.update({
    "Abu Dhabi Festival": "Abu Dhabi Festival – music, dance and cultural shows across the city.",
    "Frieze Abu Dhabi (art fair)": "Frieze Abu Dhabi – international art fair on Saadiyat Island.",
    "Mother of the Nation Festival": "Mother of the Nation Festival – family festival with rides, shows and food (Corniche).",
    "Culture Summit Abu Dhabi": "Culture Summit Abu Dhabi – conference on Saadiyat Island.",
    "Guggenheim Abu Dhabi opening": "Guggenheim Abu Dhabi opens on Saadiyat Island.",
    "Liwa International Festival": "Liwa International Festival – desert motorsports and heritage in Al Dhafra (about 2 hours away).",
    "IDEX & NAVDEX (defence exhibition)": "IDEX & NAVDEX – very large defence exhibition at ADNEC; city hotels fill up, book early.",
    "Mubadala Abu Dhabi Open (tennis)": "Mubadala Abu Dhabi Open – women's tennis tournament.",
    "Abu Dhabi International Book Fair": "Abu Dhabi International Book Fair at ADNEC.",
    "ADIPEC (energy exhibition)": "ADIPEC – world's largest energy exhibition at ADNEC; city hotels fill up, book early.",
    "Abu Dhabi Championship (golf)": "Abu Dhabi Championship – DP World Tour golf at Yas Links.",
})
SHORT = {
    "Ramadan": "Ramadan", "Eid al-Fitr": "Eid", "Eid al-Adha": "Eid", "UAE National Day": "National Day",
    "Abu Dhabi Grand Prix (F1)": "F1", "New Year": "New Year", "Abu Dhabi Festival": "AD Festival",
    "Frieze Abu Dhabi (art fair)": "Frieze", "Mother of the Nation Festival": "MOTN Festival",
    "Culture Summit Abu Dhabi": "Culture Summit", "Guggenheim Abu Dhabi opening": "Guggenheim opening",
    "Liwa International Festival": "Liwa Festival", "IDEX & NAVDEX (defence exhibition)": "IDEX",
    "Mubadala Abu Dhabi Open (tennis)": "Tennis Open", "Abu Dhabi International Book Fair": "Book Fair",
    "ADIPEC (energy exhibition)": "ADIPEC", "Abu Dhabi Championship (golf)": "Golf",
}
# long-running festivals: listed under the trip, not written on every day's bar
LONG = {"Abu Dhabi Festival", "Mother of the Nation Festival", "Liwa International Festival"}
# events that fill hotels: these days always count as busy for travelers
MAJOR = {"Eid al-Fitr", "Eid al-Adha", "UAE National Day", "Abu Dhabi Grand Prix (F1)", "New Year",
         "IDEX & NAVDEX (defence exhibition)", "ADIPEC (energy exhibition)"}
SOURCES = [
    ("Abu Dhabi events Nov 2026 – Jan 2027 (Verity Gulf)", "https://veritygulf.com/other-news/abu-dhabi-events-2026-2027-upcoming-concerts-festivals-dates-and-tickets"),
    ("Liwa International Festival dates (TradeArabia)", "https://www.tradearabia.com/News/488185/Liwa-International-Festival-2027-to-run-from-December-11-to-January-2"),
    ("IDEX & NAVDEX 2027 dates (ADNEC Group)", "https://www.adnecgroup.ae/news-media/news/details/dates-for-idex-and-navdex-2027-confirmed-with-70-of-exhibitors-committing-to-the-next-edition"),
    ("Mubadala Abu Dhabi Open 2027 (WTA)", "https://www.wtatennis.com/tournaments/2088/abu-dhabi/2027"),
    ("Abu Dhabi International Book Fair dates (ADBF)", "https://adbookfair.com/en/adibf/news-adibf/abu-dhabi-arabic-language-centre-announces-abu-dhabi-international-book-fair-dates-until-2030"),
    ("2027 F1 calendar (Khaleej Times)", "https://www.khaleejtimes.com/f1/2027-f1-calendar-announced-as-abu-dhabi-keeps-final-race"),
    ("Abu Dhabi Championship 2027 (GolfMagic)", "https://www.golfmagic.com/tour/dp-world-tour/dp-world-tour-schedule-2027"),
    ("ADIPEC 2027 (Luminik listing)", "https://www.luminik.io/events/adipec-abu-dhabi-petroleum-exhibition-conference-c8f02494ef25/"),
]

LAST_DAY = pd.Timestamp("2027-12-31")


def events_on(d) -> list:
    """All holidays + events on a day (for display)."""
    d = pd.Timestamp(d)
    out = []
    for group in (EVENTS, EXTRA_EVENTS):
        for name, spans in group.items():
            if any(pd.Timestamp(s) <= d <= pd.Timestamp(e) for s, e in spans):
                out.append(name)
    return out


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
