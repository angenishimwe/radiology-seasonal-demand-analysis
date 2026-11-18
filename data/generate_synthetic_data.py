"""
Generate a SYNTHETIC radiology exam dataset (no real patient data).

It mimics 24 months of service volume with seasonal peaks in
late July and early December. Some deliberate "messiness" is added
(spelling variants, missing values, duplicates) so the cleaning step
in the notebook is meaningful.

Usage:  python generate_synthetic_data.py
Output: anonymized_radiology_volume.csv  (same folder)
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")

BASE_DAILY = 38  # average weekday exams in a normal period


def seasonal_multiplier(d):
    """Bump around late July (Jul 20 - Aug 2) and early December (Dec 1 - Dec 14)."""
    doy = d.dayofyear
    jul_peak = pd.Timestamp(d.year, 7, 27).dayofyear
    dec_peak = pd.Timestamp(d.year, 12, 6).dayofyear
    jul = 0.45 * np.exp(-((doy - jul_peak) ** 2) / (2 * 6**2))
    dec = 0.55 * np.exp(-((doy - dec_peak) ** 2) / (2 * 6**2))
    return 1 + jul + dec


dow_effect = {0: 1.20, 1: 1.10, 2: 1.05, 3: 1.00, 4: 0.95, 5: 0.55, 6: 0.40}

modalities = ["General Radiography", "Ultrasound"]
body_parts = ["Chest", "Abdominal", "Limbs", "Spine", "Pelvic", "Head/Neck"]

rows = []
for d in dates:
    mult = seasonal_multiplier(d)
    n = rng.poisson(BASE_DAILY * dow_effect[d.dayofweek] * mult)

    # General radiography drives the surge; ultrasound rises more mildly
    p_xray = np.clip(0.62 + 0.10 * (mult - 1), 0, 0.85)
    mods = rng.choice(modalities, size=n, p=[p_xray, 1 - p_xray])

    p_in = 0.35 if d.dayofweek < 5 else 0.55  # more inpatients on weekends
    cats = rng.choice(["Inpatient", "Outpatient"], size=n, p=[p_in, 1 - p_in])

    for m, c in zip(mods, cats):
        if m == "General Radiography":
            bp = rng.choice(body_parts, p=[0.35, 0.10, 0.30, 0.15, 0.05, 0.05])
        else:
            bp = rng.choice(["Abdominal", "Pelvic", "Head/Neck"], p=[0.60, 0.30, 0.10])
        rows.append((d.strftime("%Y-%m-%d"), m, c, bp))

df = pd.DataFrame(rows, columns=["exam_date", "exam_type", "patient_category",
                                 "department_or_body_part"])
df.insert(0, "exam_id", [f"EX{str(i).zfill(6)}" for i in range(1, len(df) + 1)])

# ---- add realistic messiness ----
n_rows = len(df)

# 1) spelling / case variants in exam_type
variants = {
    "General Radiography": ["general radiography", "Gen. Radiography", "X-ray", "xray", "General Radiology"],
    "Ultrasound": ["ultrasound", "U/S", "Ultra sound", "ULTRASOUND"],
}
idx = rng.choice(n_rows, size=int(0.04 * n_rows), replace=False)
for i in idx:
    original = df.at[i, "exam_type"]
    df.at[i, "exam_type"] = rng.choice(variants[original])

# 2) missing values
for col, frac in [("department_or_body_part", 0.03), ("patient_category", 0.01)]:
    miss = rng.choice(n_rows, size=int(frac * n_rows), replace=False)
    df.loc[miss, col] = np.nan

# 3) exact duplicate rows
dups = df.sample(int(0.005 * n_rows), random_state=1)
df = pd.concat([df, dups]).sample(frac=1, random_state=7).sort_values("exam_date")

df.to_csv("anonymized_radiology_volume.csv", index=False)
print(f"Saved {len(df):,} rows covering {df.exam_date.min()} to {df.exam_date.max()}")
