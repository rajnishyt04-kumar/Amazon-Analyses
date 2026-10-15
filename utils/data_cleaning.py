
import pandas as pd
import numpy as np
from pathlib import Path

COLUMN_ALIASES = {
    "order_id": ["order_id", "order id", "orderid", "order number", "order"],
    "order_date": ["order_date", "order date", "date", "purchase date"],
    "category": ["category", "product category"],
    "product": ["product", "product name", "item"],
    "quantity": ["quantity", "qty", "units", "units sold"],
    "unit_price": ["unit_price_inr", "unit price", "price", "unit_price", "unit price inr"],
    "discount_pct": ["discount_pct", "discount", "discount percent", "discount percentage"],
    "sales": ["total_sales_inr", "total sales", "sales", "revenue", "sales revenue", "total_sales"],
    "profit": ["profit_inr", "profit", "total profit"],
    "payment_method": ["payment_method", "payment method", "payment"],
    "fulfillment": ["fulfillment", "fulfilment", "fulfillment method"],
    "order_status": ["order_status", "order status", "status"],
    "ship_state": ["ship_state", "ship state", "state", "shipping state"]
}

def normalize_columns(df):
    out = df.copy()
    out.columns = [str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in out.columns]
    # Map recognized aliases to a canonical schema while preserving unrelated columns.
    lookup = {str(c).strip().lower().replace("-", "_").replace(" ", "_"): c for c in out.columns}
    renames = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = alias.strip().lower().replace("-", "_").replace(" ", "_")
            if key in lookup:
                renames[lookup[key]] = canonical
                break
    return out.rename(columns=renames)

def clean_data(raw_df):
    """Conservative cleaning: preserve valid high-value transactions and report decisions."""
    df = normalize_columns(raw_df)
    report = {"rows_before": int(len(df)), "duplicate_rows_removed": 0, "missing_values_filled": {},
              "invalid_rows_removed": 0, "outlier_counts_iqr": {}}
    df = df.drop_duplicates().copy()
    report["duplicate_rows_removed"] = report["rows_before"] - len(df)

    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    for col in ["quantity", "unit_price", "discount_pct", "sales", "profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Strip strings and normalize whitespace; do not merge categories without evidence.
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # Report missingness; fill only categorical values with an explicit label.
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing:
            report["missing_values_filled"][col] = missing
            if pd.api.types.is_numeric_dtype(df[col]):
                # Keep missing numerical values as missing; metric functions can exclude them safely.
                continue
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            else:
                df[col] = df[col].fillna("Unknown")

    # Remove rows that cannot contribute to core sales analysis.
    required = [c for c in ["sales", "profit", "quantity"] if c in df.columns]
    before = len(df)
    if required:
        df = df.dropna(subset=required)
    if "quantity" in df.columns:
        df = df[df["quantity"] >= 0]
    if "sales" in df.columns:
        df = df[df["sales"] >= 0]
    report["invalid_rows_removed"] = int(before - len(df))

    # IQR flags are diagnostic only. Do not remove outliers automatically.
    for col in ["sales", "profit", "quantity", "unit_price"]:
        if col in df.columns and df[col].notna().sum() >= 4:
            q1, q3 = df[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            if pd.notna(iqr) and iqr > 0:
                n = int(((df[col] < q1 - 1.5*iqr) | (df[col] > q3 + 1.5*iqr)).sum())
                report["outlier_counts_iqr"][col] = n
    report["rows_after"] = int(len(df))
    return df, report
