# Sales Cleanup Report

Turns a messy sales or invoice CSV export into clean data and an Excel summary report.

Small-business exports from POS, invoicing and field-service tools are rarely clean. This tool fixes the common problems and shows exactly what it changed:

- Inconsistent headers (`Invoice Date`, `Client`, `QTY`, `Total`…) mapped to one standard layout
- Mixed date formats (`2026-09-02`, `09/05/2026`, `Sep 12 2026`)
- Currency text (`$1,250.00`, refunds written as `(129.00)`)
- Extra spaces and inconsistent capitalization in names
- Blank rows and exact duplicate rows
- Rows that can't be fixed go to a **Needs Review** sheet with the reason, and nothing is silently dropped

## Output

An Excel workbook with the sheets Overview, Monthly, By Customer, By Item, Clean Data and Needs Review. You can also save the cleaned rows as a CSV.

## Usage

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m cleanup_report sample_data/messy_sales_example.csv -o report.xlsx --clean-csv clean.csv
```

## Tests

```bash
.venv/bin/python -m pytest
```

The tests cover each cleaning rule, the full sample run, the Excel output and the command line's error handling.

The file `sample_data/messy_sales_example.csv` is **made-up example data** for demonstration only.
