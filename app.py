
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from pathlib import Path
import pandas as pd
import os, uuid
from utils.data_cleaning import clean_data
from utils.analytics import build_payload

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_BYTES = 20 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "replace-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES

# Per-session in-memory cache for small local/demo deployments. For multi-worker production, use Redis or persisted storage.
DATASETS = {}

def allowed(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def read_upload(path, sheet_name=0):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name=sheet_name)

def get_df():
    key = session.get("dataset_key", "default")
    return DATASETS.get(key, DATASETS.get("default"))

def process_df(raw):
    df, report = clean_data(raw)
    return df, report

# Load included dataset for first run.
default_path = BASE_DIR / "data" / "amazon_sales.xlsx"
if default_path.exists():
    raw = pd.read_excel(default_path)
    DATASETS["default"], _default_report = process_df(raw)

@app.get("/")
def index():
    df = get_df()
    return render_template("index.html", ready=df is not None)

@app.get("/api/dashboard")
def dashboard():
    df = get_df()
    if df is None:
        return jsonify({"error": "Upload a valid dataset to begin."}), 400
    filtered = df.copy()
    category = request.args.get("category", "")
    product = request.args.get("product", "")
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    if category and category != "All" and "category" in filtered:
        filtered = filtered[filtered["category"].astype(str) == category]
    if product and product != "All" and "product" in filtered:
        filtered = filtered[filtered["product"].astype(str) == product]
    if "order_date" in filtered:
        if start:
            filtered = filtered[filtered["order_date"] >= pd.to_datetime(start, errors="coerce")]
        if end:
            filtered = filtered[filtered["order_date"] < (pd.to_datetime(end, errors="coerce") + pd.Timedelta(days=1))]
    payload = build_payload(filtered)
    payload["row_count"] = int(len(filtered))
    return jsonify(payload)

@app.post("/api/upload")
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Choose an Excel or CSV file first."}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400
    if not allowed(file.filename):
        return jsonify({"error": "Unsupported file type. Upload .xlsx, .xls, or .csv."}), 400
    safe_name = secure_filename(file.filename)
    target = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
    file.save(target)
    try:
        if target.suffix.lower() == ".csv":
            raw = pd.read_csv(target, nrows=50000)
            sheets = []
        else:
            book = pd.ExcelFile(target)
            sheets = book.sheet_names
            sheet = request.form.get("sheet", sheets[0])
            if sheet not in sheets:
                raise ValueError("Selected worksheet does not exist.")
            raw = pd.read_excel(target, sheet_name=sheet, nrows=50000)
        if raw.empty:
            raise ValueError("The uploaded file contains no data rows.")
        df, report = process_df(raw)
        if df.empty:
            raise ValueError("No usable rows remain after validation. Check required numeric columns.")
        key = uuid.uuid4().hex
        DATASETS[key] = df
        session["dataset_key"] = key
        # Keep process cache bounded.
        while len(DATASETS) > 12:
            first = next(iter(DATASETS))
            if first == "default":
                DATASETS.pop(next(k for k in DATASETS if k != "default"), None)
            else:
                DATASETS.pop(first, None)
        return jsonify({"message": "Dataset loaded successfully.", "rows": int(len(df)),
                        "columns": list(df.columns), "sheets": sheets, "cleaning_report": report})
    except Exception as exc:
        try: target.unlink(missing_ok=True)
        except Exception: pass
        return jsonify({"error": f"Could not read this file: {str(exc)}"}), 400

@app.get("/api/columns")
def columns():
    df = get_df()
    return jsonify({"columns": list(df.columns) if df is not None else []})

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File exceeds the 20 MB upload limit."}), 413

if __name__ == "__main__":
    app.run(debug=True, port=5000)
