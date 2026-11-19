from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from cleanup_report import clean_sales, write_excel_report
from cleanup_report.clean import parse_date, parse_money, clean_name, normalize_columns
from cleanup_report.cli import main

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "messy_sales_example.csv"


def load_sample():
    return pd.read_csv(SAMPLE, dtype=str, keep_default_na=False, skip_blank_lines=False)


@pytest.mark.parametrize("raw,expected", [
    ("$1,250.00", 1250.0), ("258", 258.0), ("(129.00)", -129.0), ("-45", -45.0),
    (129, 129.0), ("", None), ("abc", None), (None, None),
])
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2026-09-02", "2026-09-02"), ("09/05/2026", "2026-09-05"),
    ("Sep 12 2026", "2026-09-12"), ("October 15 2026", "2026-10-15"),
])
def test_parse_date_valid(raw, expected):
    assert parse_date(raw) == pd.Timestamp(expected)


@pytest.mark.parametrize("raw", ["13/40/2026", "", "tomorrow", None])
def test_parse_date_invalid(raw):
    assert parse_date(raw) is None


def test_clean_name_normalizes_spacing_and_case():
    assert clean_name("  Acme   HVAC llc ") == "Acme HVAC LLC"
    assert clean_name("   ") is None


def test_missing_required_column_is_a_clear_error():
    with pytest.raises(ValueError, match="missing required columns: amount"):
        normalize_columns(pd.DataFrame(columns=["Date", "Customer", "Item", "Qty"]))


def test_sample_end_to_end_counts():
    result = clean_sales(load_sample())
    assert result.stats == {
        "rows_in": 12, "blank_rows_removed": 1, "duplicates_removed": 1,
        "rows_rejected": 3, "rows_clean": 7,
    }
    reasons = set(result.rejected["reason"])
    assert reasons == {"bad or missing date", "missing customer", "bad quantity"}
    # Refund kept as a negative line, and the total is exact.
    assert result.clean["amount"].min() == -129.0
    assert result.clean["amount"].sum() == pytest.approx(2082.50)
    assert result.clean["date"].is_monotonic_increasing


def test_excel_report_has_all_sheets(tmp_path):
    out = write_excel_report(clean_sales(load_sample()), tmp_path / "r.xlsx")
    wb = load_workbook(out)
    assert wb.sheetnames == ["Overview", "Monthly", "By Customer", "By Item", "Clean Data", "Needs Review"]
    assert wb["Clean Data"].max_row == 8  # header + 7 rows


def test_cli_success_and_error(tmp_path, capsys):
    assert main([str(SAMPLE), "-o", str(tmp_path / "r.xlsx"), "--clean-csv", str(tmp_path / "c.csv")]) == 0
    assert (tmp_path / "c.csv").read_text().count("\n") == 8
    assert main([str(tmp_path / "nope.csv")]) == 1
    assert "error:" in capsys.readouterr().err
