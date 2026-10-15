
# Amazon Sales Analytics — Tasks 1 & 2

A local-first EDA notebook and interactive Flask dashboard built from the supplied Amazon India sales workbook. Scope intentionally excludes PDF Tasks 3 and 4 (order status/revenue loss, payment/fulfillment/geographic performance).

## Included
- `notebooks/amazon_sales_analysis.ipynb`: data quality checks, conservative cleaning, KPI calculations, monthly trends, category sales/profit/units, top 10 products, distribution plots, and observations.
- `app.py`: Flask routes for the dashboard, dataset upload and dynamic filter-based metrics.
- `utils/data_cleaning.py`: schema normalization, data cleaning and diagnostic IQR outlier counts.
- `utils/analytics.py`: reusable KPI and chart aggregation functions.
- `templates/index.html`, `static/css/style.css`, `static/js/dashboard.js`: responsive interactive dashboard.
- `data/amazon_sales.xlsx`: supplied source workbook.

## Requirements
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

## Run notebook
From project root:
```bash
jupyter notebook notebooks/amazon_sales_analysis.ipynb
```
The notebook reads `data/amazon_sales.xlsx` by default. Change `DATA_PATH` in the first code cell if using another path.

## Run dashboard
```bash
python app.py
```
Open `http://127.0.0.1:5000`. The default dataset is loaded automatically. Use **Upload dataset** to replace it for the current session; supported formats are XLSX, XLS and CSV (20 MB max). The app automatically maps common column names to canonical names. For arbitrary schemas, rename/map columns to the canonical schema documented below before upload.

### Expected column mapping
Core metrics use:
- `sales` (e.g. `Total_Sales_INR`)
- `profit` (e.g. `Profit_INR`)
- `quantity` (e.g. `Quantity`)
- Optional `order_id`, `order_date`, `category`, `product`

Additional columns are retained but not used in this scoped dashboard. Common original dataset column names are mapped automatically. Uploaded workbooks with multiple sheets currently use the first worksheet; choose a sheet by adapting the upload request or use a single-sheet workbook.

## Metric definitions
- Total Sales = sum of transaction sales values.
- Total Profit = sum of transaction profit values.
- Total Orders = distinct `Order_ID` count where available; otherwise row count (the latter is a proxy, not guaranteed to be true orders).
- Units Sold = sum of `Quantity`.
- Average Order Value = Total Sales / Total Orders.
- Profit Margin = Total Profit / Total Sales × 100.

The source workbook has one row per unique `Order_ID`, but this is verified from this supplied dataset rather than assumed for all uploads. In datasets with multiple line items per order, sales/profit/quantity should be summed at line level and orders counted distinctly.

## Data-quality policy
- Exact duplicate rows are removed.
- Missing numeric/date values are reported and retained as missing; rows missing core numeric metric fields are excluded from those metrics.
- Blank categorical values are labeled `Unknown`.
- Invalid negative quantity/sales rows are excluded; valid negative profit is retained if present.
- IQR outliers are flagged and summarized, not automatically deleted. Large transactions may be genuine.
- Category imbalance is explored through group counts and distributions; no resampling is applied because this is descriptive analytics, not model training.
- Standardization/scaling is not applied to business metrics because it would reduce interpretability and is not needed for descriptive reporting.

## Security and deployment notes
Uploads are extension-checked, filenames are sanitized, and upload size is limited to 20 MB. This is a learning/demo deployment: uploaded datasets are cached in process memory and upload files are stored locally. Before public deployment, configure a strong `FLASK_SECRET_KEY`, disable debug mode, add authentication and rate limits, use managed temporary storage, and move session data to a shared store for multi-worker deployments. Do not deploy with the development secret or `debug=True`.

## Scope
Implemented only Task 1 (Overall Sales & Profit Performance) and Task 2 (Category & Product Performance). No Task 3/4 analyses or charts are included.
