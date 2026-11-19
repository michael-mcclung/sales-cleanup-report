"""Cleaning rules for a messy sales/invoice CSV export.

Handles the problems that show up in real small-business exports:
blank rows, inconsistent column names, mixed date formats, currency
strings like "$1,200.50" or "(45.00)", stray whitespace and casing in
customer names, and exact duplicate rows. Rows that can't be fixed are
kept aside with a reason instead of being silently dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

# Map the many header spellings seen in exports to one canonical name.
COLUMN_ALIASES = {
    "date": "date", "invoice date": "date", "inv date": "date", "sale date": "date",
    "customer": "customer", "client": "customer", "customer name": "customer",
    "item": "item", "product": "item", "service": "item", "description": "item",
    "qty": "quantity", "quantity": "quantity", "units": "quantity",
    "amount": "amount", "total": "amount", "price": "amount", "sale amount": "amount",
}
REQUIRED = ["date", "customer", "item", "quantity", "amount"]

_MONEY_RE = re.compile(r"^\(?-?\$?\s*[\d,]*\.?\d+\)?$")


@dataclass
class CleanResult:
    clean: pd.DataFrame
    rejected: pd.DataFrame
    stats: dict = field(default_factory=dict)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = re.sub(r"\s+", " ", str(col).strip().lower().replace("_", " "))
        if key in COLUMN_ALIASES:
            renamed[col] = COLUMN_ALIASES[key]
    df = df.rename(columns=renamed)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Export is missing required columns: {', '.join(missing)}")
    return df[REQUIRED].copy()


def parse_money(value) -> float | None:
    """'$1,200.50' -> 1200.5, '(45.00)' -> -45.0, '' -> None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or not _MONEY_RE.match(text):
        return None
    negative = text.startswith("(") and text.endswith(")") or text.startswith("-")
    digits = re.sub(r"[^\d.]", "", text)
    if not digits:
        return None
    number = float(digits)
    return -number if negative else number


def parse_date(value) -> pd.Timestamp | None:
    """Accept ISO, US (MM/DD/YYYY), and written dates; reject anything ambiguous-looking or invalid."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%b %d %Y", "%B %d %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return pd.to_datetime(text, format=fmt)
        except (ValueError, TypeError):
            continue
    return None


def clean_name(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    # Title-case but keep common business suffixes tidy.
    words = [w.upper() if w.lower() in {"llc", "inc", "hvac", "dfw", "ac"} else w.capitalize() for w in text.split(" ")]
    return " ".join(words)


def clean_sales(raw: pd.DataFrame) -> CleanResult:
    rows_in = len(raw)
    df = raw.dropna(how="all")
    df = df[~df.apply(lambda r: all(str(v).strip() == "" for v in r), axis=1)]
    blank_rows = rows_in - len(df)

    df = normalize_columns(df)
    out = pd.DataFrame({
        "date": df["date"].map(parse_date),
        "customer": df["customer"].map(clean_name),
        "item": df["item"].map(clean_name),
        "quantity": pd.to_numeric(df["quantity"], errors="coerce"),
        "amount": df["amount"].map(parse_money),
    }, index=df.index)

    reasons = pd.Series("", index=out.index, dtype=object)
    for col, msg in [("date", "bad or missing date"), ("customer", "missing customer"),
                     ("item", "missing item"), ("quantity", "bad quantity"), ("amount", "bad amount")]:
        bad = out[col].isna()
        reasons[bad] = reasons[bad].where(reasons[bad] == "", reasons[bad] + "; ") + msg

    rejected = df[reasons != ""].copy()
    rejected["reason"] = reasons[reasons != ""]

    good = out[reasons == ""].copy()
    before_dedupe = len(good)
    good = good.drop_duplicates().sort_values(["date", "customer"]).reset_index(drop=True)
    good["quantity"] = good["quantity"].astype(int)

    stats = {
        "rows_in": rows_in,
        "blank_rows_removed": blank_rows,
        "duplicates_removed": before_dedupe - len(good),
        "rows_rejected": len(rejected),
        "rows_clean": len(good),
    }
    return CleanResult(clean=good, rejected=rejected.reset_index(drop=True), stats=stats)
