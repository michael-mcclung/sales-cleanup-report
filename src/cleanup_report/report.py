"""Summaries and the Excel report."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .clean import CleanResult


def build_summary(clean: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (clean.assign(month=clean["date"].dt.to_period("M").astype(str))
               .groupby("month", as_index=False)
               .agg(orders=("amount", "size"), revenue=("amount", "sum")))
    by_customer = (clean.groupby("customer", as_index=False)
                   .agg(orders=("amount", "size"), revenue=("amount", "sum"))
                   .sort_values("revenue", ascending=False))
    by_item = (clean.groupby("item", as_index=False)
               .agg(units=("quantity", "sum"), revenue=("amount", "sum"))
               .sort_values("revenue", ascending=False))
    return {"Monthly": monthly, "By Customer": by_customer, "By Item": by_item}


def write_excel_report(result: CleanResult, path: str | Path) -> Path:
    path = Path(path)
    summary = build_summary(result.clean)
    overview = pd.DataFrame(
        [(k.replace("_", " ").capitalize(), v) for k, v in result.stats.items()]
        + [("Total revenue (clean rows)", round(float(result.clean["amount"].sum()), 2))],
        columns=["Metric", "Value"],
    )
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        overview.to_excel(xw, sheet_name="Overview", index=False)
        for name, frame in summary.items():
            frame.to_excel(xw, sheet_name=name, index=False)
        result.clean.assign(date=result.clean["date"].dt.date).to_excel(xw, sheet_name="Clean Data", index=False)
        result.rejected.to_excel(xw, sheet_name="Needs Review", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 45)
            ws.freeze_panes = "A2"
    return path
