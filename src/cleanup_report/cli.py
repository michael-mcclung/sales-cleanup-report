"""Command line: python -m cleanup_report input.csv -o report.xlsx"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from .clean import clean_sales
from .report import write_excel_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clean a messy sales CSV export and build an Excel summary report.")
    p.add_argument("input", help="CSV export to clean")
    p.add_argument("-o", "--output", default="sales_report.xlsx", help="Excel report path")
    p.add_argument("--clean-csv", help="Optional path to also save the cleaned rows as CSV")
    args = p.parse_args(argv)
    try:
        raw = pd.read_csv(args.input, dtype=str, keep_default_na=False, skip_blank_lines=False)
        result = clean_sales(raw)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_excel_report(result, args.output)
    if args.clean_csv:
        result.clean.to_csv(args.clean_csv, index=False, date_format="%Y-%m-%d")
    for k, v in result.stats.items():
        print(f"{k.replace('_', ' ')}: {v}")
    print(f"report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
