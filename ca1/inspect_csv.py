from pathlib import Path

import pandas as pd

CSV_DIR = Path("data/external")


def describe(path):
    frame = pd.read_csv(path)
    print(f"\n=== {path.name} ===")
    print(f"rows={len(frame)} columns={len(frame.columns)}")
    print(frame.dtypes.to_string())
    print("\nnull counts:")
    print(frame.isna().sum().to_string())
    print("\nfirst rows:")
    print(frame.head(3).to_string())
    date_columns = [column for column in frame.columns if "date" in column.lower()]
    for column in date_columns:
        parsed = pd.to_datetime(frame[column], errors="coerce")
        print(f"\n{column}: min={parsed.min()} max={parsed.max()} unparsable={parsed.isna().sum()}")


def main():
    files = sorted(CSV_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files found in {CSV_DIR}")
    for path in files:
        describe(path)


if __name__ == "__main__":
    main()
