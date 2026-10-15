
import pandas as pd
import numpy as np

def _sum(df, col):
    return float(df[col].sum()) if col in df.columns else None

def calculate_kpis(df):
    sales = _sum(df, "sales")
    profit = _sum(df, "profit")
    orders = int(df["order_id"].nunique()) if "order_id" in df.columns else int(len(df))
    units = _sum(df, "quantity")
    aov = (sales / orders) if sales is not None and orders else None
    margin = (profit / sales * 100) if sales not in (None, 0) and profit is not None else None
    return {"total_sales": sales, "total_profit": profit, "total_orders": orders,
            "units_sold": units, "average_order_value": aov, "profit_margin_pct": margin}

def grouped_sum(df, group_col, value_col, top_n=None):
    if group_col not in df.columns or value_col not in df.columns:
        return []
    out = df.groupby(group_col, dropna=False)[value_col].sum().sort_values(ascending=False)
    if top_n:
        out = out.head(top_n)
    return [{"label": str(k), "value": float(v)} for k, v in out.items()]

def monthly_trend(df):
    if "order_date" not in df.columns:
        return []
    d = df.dropna(subset=["order_date"]).copy()
    d["month"] = d["order_date"].dt.to_period("M").astype(str)
    cols = [c for c in ["sales", "profit"] if c in d.columns]
    if not cols:
        return []
    g = d.groupby("month", as_index=False)[cols].sum().sort_values("month")
    return g.to_dict(orient="records")

def available_filters(df):
    return {
        "categories": sorted(df["category"].dropna().astype(str).unique().tolist()) if "category" in df.columns else [],
        "products": sorted(df["product"].dropna().astype(str).unique().tolist()) if "product" in df.columns else [],
        "min_date": str(df["order_date"].min().date()) if "order_date" in df.columns and df["order_date"].notna().any() else "",
        "max_date": str(df["order_date"].max().date()) if "order_date" in df.columns and df["order_date"].notna().any() else ""
    }

def build_payload(df):
    kpis = calculate_kpis(df)
    return {
        "kpis": kpis,
        "monthly": monthly_trend(df),
        "category_sales": grouped_sum(df, "category", "sales"),
        "category_profit": grouped_sum(df, "category", "profit"),
        "category_units": grouped_sum(df, "category", "quantity"),
        "top_products": grouped_sum(df, "product", "sales", 10),
        "filters": available_filters(df)
    }
